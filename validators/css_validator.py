import tinycss2
from bs4 import Tag
from tinycss2.ast import *
from lxml.etree import fromstring, ElementBase
from cssselect import GenericTranslator, SelectorError
from typing import Optional

"""
tinycss2 docs
    https://pythonhosted.org/tinycss2/
    https://pythonhosted.org/tinycss2/#term-component-values
lxml docs
    https://lxml.de/api/
"""

"""
css precedence rules:
a more specific selector takes precedence over a less specific one
    rules that appear later in the code override earlier rules if both have the same specificity.
    A css rule with !important always takes precedence.

Specificity for single selectors from highest to lowest:
    ids (example: #main selects <div id="main">)
    classes (ex.: .myclass), attribute selectors (ex.: [href=^https:]) and pseudo-classes (ex.: :hover)
    elements (ex.: div) and pseudo-elements (ex.: ::before)
    To compare the specificity of two combined selectors, compare the number of occurences of single selectors of each of the specificity groups above.

Example: compare #nav ul li a:hover to #nav ul li.active a::after

count the number of id selectors: there is one for each (#nav)
count the number of class selectors: there is one for each (:hover and .active)
count the number of element selectors: there are 3 (ul li a) for the first and 4 for the second (ul li a ::after), thus the second combined selector is more specific.
"""


def strip(ls: []):
    """strips leading & trailing whitespace tokens"""
    while ls and ls[0].type == WhitespaceToken.type:
        ls.pop(0)
    while ls and ls[-1].type == WhitespaceToken.type:
        ls.pop()
    return ls


class CssParsingError(Exception):
    pass


def _get_xpath(selector: str) -> str:
    try:
        # todo filter out pseudo-elements (like or ::after)
        return GenericTranslator().css_to_xpath(selector)
    except SelectorError:
        raise CssParsingError()


class Rule:
    def __init__(self, selector: [], content: Declaration):
        self.selector = strip(selector)
        self.selector_str = tinycss2.serialize(self.selector)
        self.xpath = _get_xpath(self.selector_str)
        self.name = content.name
        self.value = strip(content.value)
        self.important = content.important
        self.specificity = calc_specificity(self.selector_str)

    def __repr__(self):
        return f"(Rule: {self.selector_str} | {self.name} {self.value} {'important' if self.important else ''})"


def calc_specificity(selector_str: str):  # see https://specificity.keegan.st/
    # count selectors: ID
    a = selector_str.count("#")
    # count selectors: CLASSES & PSEUDO-CLASSES & ATTRIBUTES
    b = 0
    prev = ""
    for x in selector_str:
        if x == "." or x == "[":
            b += 1
        elif x == ":" and prev != ":":
            b += 1
        prev = x
    # count selectors: ELEMENTS PSEUDO-ELEMENTS
    c = 0
    prev = ""
    for x in selector_str:
        if x.isalpha() and prev not in ".[:=\"'":
            c += 1
        elif x == ":" and prev == ":":
            c += 1
        prev = x
    # ignore pseudo-elements
    return a, b, c


class Rules:
    root: ElementBase

    def __init__(self, css_content: str):
        """parses css to Rules"""
        self.rules: [] = []
        self.map: {} = {}

        def split_on_comma(prelude: [], start=0) -> [[]]:
            """splits a list on LiteralToken with a value of a comma"""
            ps = []
            index = start
            while index < len(prelude):
                if prelude[index].type == LiteralToken.type and prelude[index].value == ",":
                    ps.append(strip(prelude[start:index]))
                    start = index + 1  # +1 because we skip the comma
                index += 1
            if start < len(prelude):
                ps.append(strip(prelude[start: len(prelude)]))
            return [y for y in ps if y]  # remove empty sublist(s) and return

        """convert a 'rule' made by tinycss2 to the Rule class I made"""
        for x in tinycss2.parse_stylesheet(css_content, skip_whitespace=True):
            if x.type == QualifiedRule.type:
                content = [x for x in tinycss2.parse_declaration_list(x.content) if x.type == Declaration.type]
                # flatten rules -> grouped selectors are seperated and then grouped rules are seperated
                for selector in split_on_comma(x.prelude):
                    for declaration in content:
                        self.rules.append(Rule(selector, declaration))
            elif x.type == ParseError.type:
                raise CssParsingError

    def __repr__(self):
        return f"RULES({len(self.rules)}): {self.rules}"

    def __len__(self):
        return len(self.rules)

    def find(self, root: ElementBase, solution_element: ElementBase, key: str) -> Optional[Rule]:
        rs: [Rule] = []
        imp: [Rule] = []
        r: Rule
        # find all rules defined for the solution element for the specified key
        for r in reversed(self.rules):
            if r.name == key:
                for element in root.xpath(r.xpath):
                    if element == solution_element:
                        if r.important:
                            imp.append(r)
                        else:
                            rs.append(r)
        # check if there are rules containing !important
        if imp:
            rs = imp

        # no rules found
        if not rs:
            return None
        # get the most specific rule or the one that was defined the latest if multiple with the same specificity
        dom_rule = rs[0]  # the dominating rule
        for r in rs:
            # if   less  than: r is overruled by dom_rule because dom_rule has a higher specificity
            # if  equal  than: r is overruled by dom_rule because dom_rule was defined after r
            # if greater than: r overrules dom_rules because of higher specificity
            if r.specificity > dom_rule.specificity:
                dom_rule = r

        return tinycss2.serialize(dom_rule.value)


class AmbiguousXpath(Exception):
    pass


class CssValidator:
    def __init__(self, html, css):
        self.root: ElementBase = fromstring(html)
        self.rules = Rules(css)
        self.rules.root = self.root
        self.xpaths = {}

    def get_xpath_soup(self, element):
        # memorization of the xpath_soup method
        if id(element) not in self.xpaths:
            self.xpaths.update({id(element): self._get_xpath_soup(element)})
        return self.xpaths[id(element)]

    # 6250 -> 50 calls
    def _get_xpath_soup(self, element):
        components = []
        child = element if element.name else element.parent
        for parent in child.parents:
            siblings = parent.find_all(child.name, recursive=False)
            components.append(
                child.name if 1 == len(siblings) else '%s[%d]' % (
                    child.name,
                    next(i for i, s in enumerate(siblings, 1) if s is child)
                )
            )
            child = parent
        components.reverse()
        return '/%s' % '/'.join(components)

    def find(self, element: Tag, key: str):
        xpath_solution = self.get_xpath_soup(element)
        sols = self.root.xpath(xpath_solution)
        if not len(sols) == 1:
            raise AmbiguousXpath()
        return self.rules.find(self.root, sols[0], key)
