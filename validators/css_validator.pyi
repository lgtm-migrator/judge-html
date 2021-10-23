from typing import Optional

from bs4.element import Tag
from lxml.etree import ElementBase
from tinycss2.ast import Declaration

from utils.color_converter import Color


def strip(ls: list) -> list: ...


class CssParsingError(Exception):
    pass


def _get_xpath(selector: str) -> str: ...


class Rule:
    selector: list
    selector_str: str
    xpath: str
    name: str
    value: list
    important: bool
    specificity: tuple[int, int, int]
    value_str: str
    color: Optional[Color]

    def __init__(self, selector: list, content: Declaration): ...

    def __repr__(self) -> str: ...

    def is_color(self) -> bool: ...

    def has_color(self, color: str) -> bool: ...



def calc_specificity(selector_str: str) -> tuple[int, int, int]:  ...

class Rules:
    root: ElementBase
    rules: list
    map: dict

    def __init__(self, css_content: str): ...

    def __repr__(self) -> str: ...

    def __len__(self) -> int: ...

    def find(self, root: ElementBase, solution_element: ElementBase, key: str) -> Optional[Rule]: ...

    def find_all(self, root: ElementBase, solution_element: ElementBase) -> dict[str, Rule]: ...


class AmbiguousXpath(Exception):
    pass


class CssValidator:
    root: Optional[ElementBase]
    rules: Rules
    xpaths: dict

    def __init__(self, html: str): ...
    
    def __bool__(self): ...

    def get_xpath_soup(self, element: Tag) -> str: ...

    def _get_xpath_soup(self, element: Tag) -> str: ...

    def find(self, element: Tag, key: str) -> Optional[Rule]: ...
