from html.parser import HTMLParser
from exceptions.htmlExceptions import *
from os import path
from utils.file_loaders import json_loader, html_loader

# Location of this test file
base_path = path.dirname(__file__)
# keynames for the json
REQUIRED_ATR_KEY = "required_attributes"
RECOMMENDED_ATR_KEY = "recommended_attributes"
CLOSING_TAG_OMISSION_KEY = "closing_tag_omission"
PERMITTED_PARENTS_KEY = "permitted_parents"


class HtmlValidator(HTMLParser):
    """
    parses & validates the html
      the html doesn't need to start with <!DOCTYPE html>, if it is present it will just be ignored
    this class checks the following:
      * each tag that opens must have a corresponding closing tag
        * tags starting with </ are omitted
        * tags that dont need a closing tag (see json) can bit omitted (like <meta>)
      * is the tag a valid tag
      * does the tag have valid nesting (it checks the permitted parents)
          for example a head tag has the html tag as permitted parent but nothing else
      * required attributes (to be completed in the json)
      * recommended attributes (to be completed in the json)
    """

    def __init__(self, **kwargs):
        super().__init__()
        self.warnings = Warnings()
        self.tag_stack = []
        self.valid_dict = json_loader(path.abspath(path.join(base_path, "html_tags_attributes.json")))
        self.check_required = kwargs.get("required", True)
        self.check_recommended = kwargs.get("recommended", True)
        self.check_nesting = kwargs.get('nesting', True)

    def set_check_required(self, b: bool):
        self.check_required = b

    def set_check_recommended(self, b: bool):
        self.check_recommended = b

    def set_check_nesting(self, b: bool):
        self.check_nesting = b

    def validate_file(self, source_filepath: str):
        self._validate(html_loader(source_filepath, shorted=False))

    def validate_content(self, content: str):
        self._validate(content)

    def _validate(self, text: str):
        self.tag_stack.clear()
        self.warnings.clear()
        self.reset()
        # check brackets and stuff ( '(', '"', '{', '[', '<')
        self._valid_chars(text)
        # check html syntax
        self.feed(text)
        while self.tag_stack:  # clear tag stack
            if not self._is_omittable(self.tag_stack[-1]):
                raise MissingClosingTagError(self.tag_stack.pop(), self.tag_stack, self.getpos())
            self.tag_stack.pop()
        if self.warnings:
            raise self.warnings

    def error(self, error: HtmlValidationError):  # make exception classes and throw these instead
        raise error

    def warning(self, warning: HtmlValidationError):
        self.warnings.add(warning)

    def _valid_chars(self, text: str):
        stack = []
        pos_stack = []
        convert = {
            "(": ")",
            "<": ">",
            "'": "'",
            '"': '"'
        }
        convert.update({val: key for key, val in convert.items()})  # put the inverse map in the map
        text = list(text)
        i = 0
        end = len(text)
        # loop text
        while i < end:
            char = text[i]
            # closing
            if stack and convert[stack[-1]] == char:
                stack.pop()
                pos_stack.pop()
            # not closing
            elif char in convert:
                stack.append(char)
                pos_stack.append(i + 1)  # humans count from 1 not from 0
            i += 1
        print(len(stack))
        print(stack)
        print(pos_stack)

    def handle_starttag(self, tag: str, attributes: [(str, str)]):
        self._valid_tag(tag)
        # already append, because the tag is valid,
        #  this way the tag stack is updated for a more accurate location of the error messages
        if self.check_nesting:
            self._valid_nesting(tag)
        self.tag_stack.append(tag)
        self._valid_attributes(tag, set(a[0] for a in attributes))

    def handle_endtag(self, tag: str):
        self._validate_corresponding_tag(tag)
        self.tag_stack.pop()

    def handle_data(self, data: str):
        pass  # we don't need to ook at data

    def _validate_corresponding_tag(self, tag: str):
        """validate that each tag that opens has a corresponding closing tag
        """
        if not self.tag_stack:
            self.error(MissingClosingTagError(tag, self.tag_stack, self.getpos()))

        if tag != self.tag_stack[-1]:
            while self._is_omittable(self.tag_stack[-1]):
                self.tag_stack.pop()
            if tag != self.tag_stack[-1]:
                self.error(MissingClosingTagError(self.tag_stack[-1], self.tag_stack, self.getpos()))

    def _is_omittable(self, tag: str) -> bool:
        return CLOSING_TAG_OMISSION_KEY in self.valid_dict[tag] \
               and self.valid_dict[tag][CLOSING_TAG_OMISSION_KEY]

    def _valid_tag(self, tag: str):
        """validate that a tag is a valid HTML tag"""
        if tag not in self.valid_dict:
            self.error(InvalidTagError(tag, self.tag_stack, self.getpos()))

    def _valid_attributes(self, tag: str, attributes: set[str]):
        """validate attributes"""
        tag_info = self.valid_dict[tag]

        if self.check_required:
            required = set(tag_info[REQUIRED_ATR_KEY]) if REQUIRED_ATR_KEY in tag_info else set()
            if missing_req := (required - attributes):
                self.error(MissingRequiredAttributeError(tag, ", ".join(missing_req), self.tag_stack, self.getpos()))

        if self.check_recommended:
            recommended = set(tag_info[RECOMMENDED_ATR_KEY]) if RECOMMENDED_ATR_KEY in tag_info else set()
            if missing_rec := (recommended - attributes):
                self.warning(MissingRecommendedAttributesWarning(tag, ", ".join(missing_rec), self.tag_stack.copy(),
                                                                 self.getpos()))

    def _valid_nesting(self, tag):
        tag_info = self.valid_dict[tag]
        if PERMITTED_PARENTS_KEY in tag_info:
            # check if the prev tag is in the permitted parents field of the current tag
            prev_tag = self.tag_stack[-1] if self.tag_stack else None
            # prev tag can be None when tag is <html>, you don't expect it has a parent,
            #   if you want a tag without a parent you need to add "permitted_parent: []" in the json for that tag
            if not tag_info[PERMITTED_PARENTS_KEY]:
                if prev_tag is not None:
                    self.error(UnexpectedTagError(tag, self.tag_stack, self.getpos()))
            elif prev_tag is not None and prev_tag not in tag_info[PERMITTED_PARENTS_KEY]:
                self.error(UnexpectedTagError(tag, self.tag_stack, self.getpos()))


