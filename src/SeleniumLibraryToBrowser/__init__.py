import re
import time
import typing
from datetime import timedelta
from enum import Enum
from itertools import count
from typing import Any, List, Optional, Union

from Browser import Browser
from Browser.assertion_engine import AssertionOperator as AO
from Browser.utils.data_types import *
from robot.api import logger
from robot.api.deco import keyword, library
from robot.libraries.BuiltIn import BuiltIn
from robot.utils import DotDict, secs_to_timestr

EQUALS = AO["=="]
NOT_EQUALS = AO["!="]
CONTAINS = AO["*="]
NOT_CONTAINS = AO["not contains"]
STARTS_WITH = AO["^="]
ENDS_WITH = AO["$="]
THEN = AO["then"]
VALIDATE = AO["validate"]
GREATER_THAN = AO[">"]


class WebElement(str):
    # self._key_attrs = {
    #         None: ["@id", "@name"],
    #         "a": [
    #             "@id",
    #             "@name",
    #             "@href",
    #             "normalize-space(descendant-or-self::text())",
    #         ],
    #         "img": ["@id", "@name", "@src", "@alt"],
    #         "input": ["@id", "@name", "@value", "@src"],
    #         "button": [
    #             "@id",
    #             "@name",
    #             "@value",
    #             "normalize-space(descendant-or-self::text())",
    #         ],
    #     }

    # def _get_tag_and_constraints(self, tag):
    #     if tag is None:
    #         return None, {}
    #     tag = tag.lower()
    #     constraints = {}
    #     if tag == "link":
    #         tag = "a"
    #     if tag == "partial link":
    #         tag = "a"
    #     elif tag == "image":
    #         tag = "img"
    #     elif tag == "list":
    #         tag = "select"
    #     elif tag == "radio button":
    #         tag = "input"
    #         constraints["type"] = "radio"
    #     elif tag == "checkbox":
    #         tag = "input"
    #         constraints["type"] = "checkbox"
    #     elif tag == "text field":
    #         tag = "input"
    #         constraints["type"] = [
    #             "date",
    #             "datetime-local",
    #             "email",
    #             "month",
    #             "number",
    #             "password",
    #             "search",
    #             "tel",
    #             "text",
    #             "time",
    #             "url",
    #             "week",
    #             "file",
    #         ]
    #     elif tag == "file upload":
    #         tag = "input"
    #         constraints["type"] = "file"
    #     elif tag == "text area":
    #         tag = "textarea"
    #     return tag, constraints

    LOCATORS = {
        "id": "id={loc}",
        "name": "css=[name={loc}]",
        "identifier": "css=[id={loc}], [name={loc}]",
        "class": "css=.{loc}",
        "tag": "css={loc}",
        "xpath": "xpath={loc}",
        "css": "css={loc}",
        "link": 'css=a >> text="{loc}"',
        "partial link": "css=a >> text={loc}",
        "default": "[id={loc}], [name={loc}]",
        "text": "text={loc}",
        "element": "element={loc}",
    }

    @classmethod
    def from_string(cls, locator: str) -> "WebElement":
        for illegal_loc in ["dom", "sizzle", "jquery", "data"]:
            match = re.match(f"{illegal_loc} ?[:=] ?", locator)
            if match:
                raise ValueError(
                    f"Invalid locator strategy '{illegal_loc}'.\n"
                    f"Please use a supported locator strategy instead.\n"
                    f"{list(cls.LOCATORS.keys())}"
                )
        for strategy, selector in cls.LOCATORS.items():
            match = re.match(f"{strategy} ?[:=] ?", locator)
            if match:
                loc = locator[match.end() :]
                return cls(selector.format(loc=loc))
        if re.match(r"\(*//", locator):
            return cls(f"xpath={locator}")
        return cls("[id='{loc}'], [name='{loc}']".format(loc=locator))

    @staticmethod
    def is_default(locator: str) -> bool:
        match = re.fullmatch(r"\[id='(.*)'], \[name='(.*)']", locator)
        if match and match.group(1) == match.group(2):
            return match.group(1)
        return None


BROWSERS = {
    "firefox": (SupportedBrowsers.firefox, False),
    "ff": (SupportedBrowsers.firefox, False),
    "headlessfirefox": (SupportedBrowsers.firefox, True),
    "chromium": (SupportedBrowsers.chromium, False),
    "chrome": (SupportedBrowsers.chromium, False),
    "googlechrome": (SupportedBrowsers.chromium, False),
    "headlesschrome": (SupportedBrowsers.chromium, True),
    "gc": (SupportedBrowsers.chromium, False),
    "edge": (SupportedBrowsers.chromium, False),
    "webkit": (SupportedBrowsers.webkit, False),
    "safari": (SupportedBrowsers.webkit, False),
}


@library(converters={WebElement: WebElement.from_string})
class SeleniumLibraryToBrowser:
    def __init__(
        self,
        timeout=timedelta(seconds=5.0),
        implicit_wait=timedelta(seconds=0.0),
        run_on_failure="Capture Page Screenshot",
        screenshot_root_directory: Optional[str] = None,
        plugins: Optional[str] = None,
        event_firing_webdriver: Optional[str] = None,
        browser_args: Optional[List[str]] = None,
    ):
        self.timeout = timeout
        self.implicit_wait = implicit_wait
        self.run_on_failure = run_on_failure
        self.screenshot_root_directory = screenshot_root_directory
        self.plugins = plugins
        self.event_firing_webdriver = event_firing_webdriver
        self._browser: Optional[Browser] = None
        self._browser_args = browser_args or []
        self._browser_indexes = {}
        self._browser_aliases = {}
        self._browser_index = count()

    @property
    def b(self) -> Browser:
        if self._browser is None:
            BuiltIn().import_library(name="Browser", *self._browser_args)
            self._browser = BuiltIn().get_library_instance("Browser")
            self._browser.set_strict_mode(False, Scope.Global)
            BuiltIn().set_library_search_order("SeleniumLibraryToBrowser")
        return self._browser

    def get_button_locator(self, locator: WebElement) -> WebElement:
        loc = WebElement.is_default(locator)
        if loc:
            loc = loc.replace('"', '\\"')
            locator = (
                "xpath="
                f'//button[@id="{loc}"]|'
                f'//button[@name="{loc}"]|'
                f'//button[@value="{loc}"]|'
                f'//button[.="{loc}"]|'
                f'//input[@id="{loc}"]|'
                f'//input[@name="{loc}"]|'
                f'//input[@value="{loc}"]|'
                f'//input[.="{loc}"]'
            )
        return locator

    def get_link_locator(self, locator: WebElement) -> WebElement:
        loc = WebElement.is_default(locator)
        if loc:
            xpath = (
                'xpath=//a[@id="{loc}"] | '
                '//a[@name="{loc}"] | '
                '//a[@href="{loc}"] | '
                '//a[normalize-space(descendant-or-self::text())="{loc}"]'
            )
            if '"' in loc:
                xpath = xpath.replace('"', "'")
            locator = xpath.format(loc=loc)
        return locator

    def get_image_locator(self, locator: WebElement) -> WebElement:
        loc = WebElement.is_default(locator)
        if loc:
            locator = (
                f'xpath=//img[@id="{loc}"] | '
                f'//img[@name="{loc}"] | '
                f'//img[@src="{loc}"] | '
                f'//img[@alt="{loc}"]'
            )
        return locator

    def get_list_locator(self, locator: WebElement) -> WebElement:
        loc = WebElement.is_default(locator)
        if loc:
            locator = (
                f'xpath=//select[@id="{loc}"] | '
                f'//select[@name="{loc}"] | '
                f'//select[@value="{loc}"]'
            )
        return locator

    def page_contains(self, locator):
        self.b.set_selector_prefix(None, scope=Scope.Global)
        if self.b.get_element_count(locator):
            return True
        cnt = self.b.get_element_count("iframe, frame")
        for index in range(cnt):
            if self.b.get_element_count(f"iframe, frame >> nth={index} >>> {locator}"):
                return True
        return False

    @keyword
    def add_cookie(
        self,
        name: str,
        value: str,
        path: Optional[str] = None,
        domain: Optional[str] = None,
        secure: Optional[bool] = None,
        expiry: Optional[str] = None,
    ):
        "*NOT IMPLEMENTED YET*"
        raise NotImplementedError("keyword is not implemented")

    @keyword
    def add_location_strategy(
        self, strategy_name: str, strategy_keyword: str, persist: bool = False
    ):
        "*NOT IMPLEMENTED YET*"
        raise NotImplementedError("keyword is not implemented")

    @keyword
    def alert_should_be_present(
        self,
        text: str = "",
        action: str = "ACCEPT",
        timeout: Optional[timedelta] = None,
    ):
        "*NOT IMPLEMENTED YET*"
        raise NotImplementedError("keyword is not implemented")

    @keyword
    def alert_should_not_be_present(
        self, action: str = "ACCEPT", timeout: Optional[timedelta] = None
    ):
        "*NOT IMPLEMENTED YET*"
        raise NotImplementedError("keyword is not implemented")

    @keyword
    def assign_id_to_element(self, locator: WebElement, id: str):
        "*NOT IMPLEMENTED YET*"
        raise NotImplementedError("keyword is not implemented")

    @keyword(tags=("IMPLEMENTED",))
    def capture_element_screenshot(
        self,
        locator: Optional[WebElement],
        filename: str = "selenium-element-screenshot-{index}.png",
    ):
        self.b.take_screenshot(filename=re.sub(".png$", "", filename), selector=locator)

    @keyword(tags=("IMPLEMENTED",))
    def capture_page_screenshot(self, filename: str = "selenium-screenshot-{index}.png"):
        self.b.take_screenshot(filename=re.sub(".png$", "", filename))

    @keyword(tags=("IMPLEMENTED",))
    def checkbox_should_be_selected(self, locator: WebElement):
        if not (
            self.b.get_attribute(locator, "type").lower() == "checkbox"
            and self.b.get_property(locator, "nodeName") == "INPUT"
        ):
            raise ValueError("Element is not a checkbox")
        self.b.get_checkbox_state(locator, EQUALS, True)

    @keyword(tags=("IMPLEMENTED",))
    def checkbox_should_not_be_selected(self, locator: WebElement):
        if not (
            self.b.get_attribute(locator, "type").lower() == "checkbox"
            and self.b.get_property(locator, "nodeName") == "INPUT"
        ):
            raise ValueError("Element is not a checkbox")
        self.b.get_checkbox_state(locator, EQUALS, False)

    @keyword(tags=("IMPLEMENTED",))
    def choose_file(self, locator: WebElement, file_path: str):
        self.b.upload_file_by_selector(locator, file_path)

    @keyword(tags=("IMPLEMENTED",))
    def clear_element_text(self, locator: WebElement):
        self.b.clear_text(locator)

    @keyword(tags=("IMPLEMENTED",))
    def click_button(self, locator: WebElement, modifier: Union[bool, str] = False):
        if modifier:
            raise NotImplementedError("Modifier is not implemented")
        locator = self.get_button_locator(locator)
        self.b.click(selector=locator)

    @keyword(tags=("IMPLEMENTED",))
    def click_element(
        self,
        locator: WebElement,
        modifier: Union[bool, str] = False,
        action_chain: bool = False,
    ):
        if modifier:
            raise NotImplementedError("Modifier is not implemented")
        self.b.click(selector=locator)

    @keyword(tags=("IMPLEMENTED",))
    def click_element_at_coordinates(self, locator: WebElement, xoffset: int, yoffset: int):
        bbox = self.b.get_boundingbox(selector=locator)  # {x, y, width, height}
        # calculates the half of the width and height of the element
        x = bbox["width"] / 2 + xoffset
        y = bbox["height"] / 2 + yoffset
        self.b.click(selector=locator, position_x=x, position_y=y)

    @keyword(tags=("IMPLEMENTED",))
    def click_image(self, locator: WebElement, modifier: Union[bool, str] = False):
        """See the Locating elements section for details about the locator syntax.
        When using the default locator strategy, images are searched using id, name, src and alt.
        """
        if modifier:
            raise NotImplementedError("Modifier is not implemented")
        locator = self.get_image_locator(locator)
        self.b.click(selector=locator)

    @keyword(tags=("IMPLEMENTED",))
    def click_link(self, locator: WebElement, modifier: Union[bool, str] = False):
        """See the Locating elements section for details about the locator syntax.
        When using the default locator strategy, links are searched using id, name,
        href and the link text.
        """
        if modifier:
            raise NotImplementedError("Modifier is not implemented")
        locator = self.get_link_locator(locator)
        self.b.click(selector=locator)

    @keyword(tags=("IMPLEMENTED",))
    def close_all_browsers(self):
        self.b.close_browser(SelectionType.ALL)
        self._browser_aliases = {}
        self._browser_indexes = {}

    @keyword(tags=("IMPLEMENTED",))
    def close_browser(self):
        current_id = self.b.get_browser_ids(SelectionType.ACTIVE)
        for index, id in self._browser_indexes.items():
            if id == current_id:
                self._browser_indexes.pop(index)
                for alias, idx in self._browser_aliases.items():
                    if idx == index:
                        self._browser_aliases.pop(alias)
                        break
                break
        self.b.close_browser(SelectionType.CURRENT)

    @keyword(tags=("IMPLEMENTED",))
    def close_window(self):
        self.b.close_page(SelectionType.CURRENT)

    @keyword
    def cover_element(self, locator: WebElement):
        "*NOT IMPLEMENTED YET*"
        raise NotImplementedError("keyword is not implemented")

    @keyword
    def create_webdriver(
        self, driver_name: str, alias: Optional[str] = None, kwargs=None, **init_kwargs
    ):
        "*NOT IMPLEMENTED YET*"
        raise NotImplementedError("keyword is not implemented")

    @keyword
    def current_frame_should_contain(self, text: str, loglevel: str = "TRACE"):
        "*NOT IMPLEMENTED YET*"
        raise NotImplementedError("keyword is not implemented")

    @keyword
    def current_frame_should_not_contain(self, text: str, loglevel: str = "TRACE"):
        "*NOT IMPLEMENTED YET*"
        raise NotImplementedError("keyword is not implemented")

    @keyword(tags=("IMPLEMENTED",))
    def delete_all_cookies(self):
        self.b.delete_all_cookies()

    @keyword
    def delete_cookie(self, name):
        "*NOT IMPLEMENTED YET*"
        raise NotImplementedError("keyword is not implemented")

    @keyword(tags=("IMPLEMENTED",))
    def double_click_element(self, locator: WebElement):
        self.b.click(locator, clickCount=2, delay=timedelta(milliseconds=100))

    @keyword(tags=("IMPLEMENTED",))
    def drag_and_drop(self, locator: WebElement, target: WebElement):
        self.b.drag_and_drop(locator, target, steps=10)

    @keyword(tags=("IMPLEMENTED",))
    def drag_and_drop_by_offset(self, locator: WebElement, xoffset: int, yoffset: int):
        self.b.drag_and_drop_relative_to(locator, xoffset, yoffset, steps=10)

    @keyword(tags=("IMPLEMENTED",))
    def element_attribute_value_should_be(
        self,
        locator: WebElement,
        attribute: str,
        expected: Optional[str],
        message: Optional[str] = None,
    ):
        self.b.get_attribute(locator, attribute, EQUALS, expected, message)

    @keyword(tags=("IMPLEMENTED",))
    def element_should_be_disabled(self, locator: WebElement):
        self.b.get_element_states(locator, VALIDATE, "(readonly | disabled) & value")

    @keyword(tags=("IMPLEMENTED",))
    def element_should_be_enabled(self, locator: WebElement):
        self.b.get_element_states(locator, VALIDATE, "not bool((readonly | disabled) & value)")

    @keyword(tags=("IMPLEMENTED",))
    def element_should_be_focused(self, locator: WebElement):
        self.b.get_element_states(locator, CONTAINS, "focused")

    @keyword(tags=("IMPLEMENTED",))
    def element_should_be_visible(self, locator: WebElement, message: Optional[str] = None):
        self.b.get_element_states(locator, CONTAINS, "visible", message=message)

    @keyword(tags=("IMPLEMENTED",))
    def element_should_contain(
        self,
        locator: WebElement,
        expected: Optional[str],
        message: Optional[str] = None,
        ignore_case: bool = False,
    ):
        if ignore_case:
            self.b.get_text(
                locator, VALIDATE, f"'''{expected}'''.lower() in value.lower()", message
            )
        else:
            self.b.get_text(locator, CONTAINS, expected, message)

    @keyword(tags=("IMPLEMENTED",))
    def element_should_not_be_visible(self, locator: WebElement, message: Optional[str] = None):
        self.b.get_element_states(locator, NOT_CONTAINS, "visible", message=message)

    @keyword(tags=("IMPLEMENTED",))
    def element_should_not_contain(
        self,
        locator: WebElement,
        expected: Optional[str],
        message: Optional[str] = None,
        ignore_case: bool = False,
    ):
        if ignore_case:
            self.b.get_text(
                locator, VALIDATE, f"'''{expected}'''.lower() not in value.lower()", message
            )
        else:
            self.b.get_text(locator, AO["not contains"], expected, message)

    @keyword(tags=("IMPLEMENTED",))
    def element_text_should_be(
        self,
        locator: WebElement,
        expected: Optional[str],
        message: Optional[str] = None,
        ignore_case: bool = False,
    ):
        if ignore_case:
            self.b.get_text(
                locator, VALIDATE, f"'''{expected}'''.lower() == value.lower()", message
            )
        else:
            self.b.get_text(locator, EQUALS, expected, message)

    @keyword(tags=("IMPLEMENTED",))
    def element_text_should_not_be(
        self,
        locator: WebElement,
        not_expected: Optional[str],
        message: Optional[str] = None,
        ignore_case: bool = False,
    ):
        if ignore_case:
            self.b.get_text(
                locator, VALIDATE, f"'''{not_expected}'''.lower() not in value.lower()", message
            )
        else:
            self.b.get_text(locator, NOT_EQUALS, not_expected, message)

    @keyword
    def execute_async_javascript(self, *code: WebElement):
        "*NOT IMPLEMENTED YET*"
        raise NotImplementedError("keyword is not implemented")

    @keyword
    def execute_javascript(self, *code: WebElement):
        "*NOT IMPLEMENTED YET*"
        raise NotImplementedError("keyword is not implemented")

    @keyword
    def frame_should_contain(self, locator: WebElement, text: str, loglevel: str = "TRACE"):
        "*NOT IMPLEMENTED YET*"
        raise NotImplementedError("keyword is not implemented")

    @keyword(tags=("IMPLEMENTED",))
    def get_all_links(self):
        return [
            self.b.get_attribute(element, "id")
            if "id" in self.b.get_attribute_names(element)
            else ""
            for element in self.b.get_elements(selector="css=a")
        ]

    @keyword(tags=("IMPLEMENTED",))
    def get_browser_aliases(self):
        return DotDict(self._browser_aliases)

    @keyword(tags=("IMPLEMENTED",))
    def get_browser_ids(self):
        return list(self._browser_indexes.keys())

    @keyword(tags=("IMPLEMENTED",))
    def get_cookie(self, name: str):
        return DotDict(self.b.get_cookie(name, CookieType.dict))

    @keyword(tags=("IMPLEMENTED",))
    def get_cookies(self, as_dict: bool = False):
        if as_dict:
            return DotDict(self.b.get_cookies(CookieType.dictionary))
        return self.b.get_cookies(CookieType.str)

    @keyword(tags=("IMPLEMENTED",))
    def get_element_attribute(self, locator: WebElement, attribute: str):
        return self.b.get_attribute(locator, attribute)

    @keyword(tags=("IMPLEMENTED",))
    def get_element_count(self, locator: WebElement):
        return self.b.get_element_count(locator)

    @keyword(tags=("IMPLEMENTED",))
    def get_element_size(self, locator: WebElement):
        value = self.b.get_boundingbox(locator, BoundingBoxFields.ALL)
        return value["width"], value["height"]

    @keyword(tags=("IMPLEMENTED",))
    def get_horizontal_position(self, locator: WebElement):
        return self.b.get_boundingbox(locator, BoundingBoxFields.x)

    @keyword(tags=("IMPLEMENTED",))
    def get_list_items(self, locator: WebElement, values: bool = False):
        options = self.b.get_select_options(locator)
        if values:
            return [option["value"] for option in options]
        return [option["label"] for option in options]

    @keyword(tags=("IMPLEMENTED",))
    def get_location(self):
        return self.b.get_url()

    @keyword(tags=("IMPLEMENTED",))
    def get_locations(self, browser: str = "CURRENT"):
        current_page = self.b.get_page_ids(
            page=SelectionType.CURRENT, context=SelectionType.CURRENT, browser=SelectionType.CURRENT
        )[0]
        try:
            return list(self._generate_locations(browser))
        finally:
            self.b.switch_page(current_page, context=SelectionType.ALL, browser=SelectionType.ALL)

    def _generate_locations(self, browser: str):
        for page_id in self._get_page_ids(browser):
            self.b.switch_page(page_id, context=SelectionType.ALL, browser=SelectionType.ALL)
            yield self.b.get_url()

    def _get_page_ids(self, browser: str):
        if browser.upper() == "CURRENT":
            return self.b.get_page_ids(browser=SelectionType.CURRENT)
        if browser.upper() == "ALL":
            return self.b.get_page_ids()

        id = self._browser_indexes.get(browser, None) or self._browser_indexes.get(
            self._browser_aliases.get(browser), None
        )
        if id is None:
            raise ValueError(f"Browser '{browser}' not found")
        org_browser = self.b.switch_browser(id)
        try:
            return self.b.get_page_ids(browser=SelectionType.CURRENT)
        finally:
            self.b.switch_browser(org_browser)

    @keyword(tags=("IMPLEMENTED",))
    def get_selected_list_label(self, locator: WebElement):
        selected_labels = self.b.get_selected_options(locator, SelectAttribute.label)
        try:
            return selected_labels[0]
        except IndexError:
            return None

    @keyword(tags=("IMPLEMENTED",))
    def get_selected_list_labels(self, locator: WebElement):
        return self.b.get_selected_options(locator, SelectAttribute.label)

    @keyword(tags=("IMPLEMENTED",))
    def get_selected_list_value(self, locator: WebElement):
        selected_values = self.b.get_selected_options(locator, SelectAttribute.value)
        try:
            return selected_values[0]
        except IndexError:
            return None

    @keyword(tags=("IMPLEMENTED",))
    def get_selected_list_values(self, locator: WebElement):
        return self.b.get_selected_options(locator, SelectAttribute.value)

    @keyword(tags=("IMPLEMENTED",))
    def get_selenium_implicit_wait(self):
        return self.b.timeout

    @keyword
    def get_selenium_speed(self):
        "*NOT IMPLEMENTED YET*"
        raise NotImplementedError("keyword is not implemented")

    @keyword(tags=("IMPLEMENTED",))
    def get_selenium_timeout(self):
        return self.b.timeout

    @keyword
    def get_session_id(self):
        "*NOT IMPLEMENTED YET*"
        raise NotImplementedError("keyword is not implemented")

    @keyword
    def get_source(self):
        self.b.get_page_source()

    @keyword(tags=("IMPLEMENTED",))
    def get_table_cell(
        self,
        locator: Optional[WebElement],
        row: int,
        column: int,
        loglevel: str = "TRACE",
    ):
        try:
            element = self.b.get_table_cell_element(locator, column, row)
            return self.b.get_text(element)
        except Exception as e:
            self.log_source(loglevel)
            raise e

    @keyword(tags=("IMPLEMENTED",))
    def get_text(self, locator: WebElement):
        return self.b.get_text(locator)

    @keyword(tags=("IMPLEMENTED",))
    def get_title(self):
        return self.b.get_title()

    @keyword(tags=("IMPLEMENTED",))
    def get_value(self, locator: WebElement):
        return self.b.get_text(locator)

    @keyword(tags=("IMPLEMENTED",))
    def get_vertical_position(self, locator: WebElement):
        return self.b.get_boundingbox(locator, BoundingBoxFields.y)

    @keyword(tags=("IMPLEMENTED",))
    def get_webelement(self, locator: WebElement):
        return self.b.get_element(locator)

    @keyword(tags=("IMPLEMENTED",))
    def get_webelements(self, locator: WebElement):
        return self.b.get_elements(locator)

    @keyword
    def get_window_handles(self, browser: str = "CURRENT"):
        "*NOT IMPLEMENTED YET*"
        raise NotImplementedError("keyword is not implemented")

    @keyword
    def get_window_identifiers(self, browser: str = "CURRENT"):
        "*NOT IMPLEMENTED YET*"
        raise NotImplementedError("keyword is not implemented")

    @keyword
    def get_window_names(self, browser: str = "CURRENT"):
        "*NOT IMPLEMENTED YET*"
        raise NotImplementedError("keyword is not implemented")

    @keyword
    def get_window_position(self):
        "*NOT IMPLEMENTED YET*"
        raise NotImplementedError("keyword is not implemented")

    @keyword(tags=("IMPLEMENTED",))
    def get_window_size(self, inner: bool = False):
        scope = "inner" if inner else "outer"
        return self.b.evaluate_javascript(
            None, f"() => [window.{scope}Width, window.{scope}Height]"
        )

    @keyword(tags=("IMPLEMENTED",))
    def get_window_titles(self, browser: str = "CURRENT"):
        current_page = self.b.get_page_ids(
            page=SelectionType.CURRENT, context=SelectionType.CURRENT, browser=SelectionType.CURRENT
        )[0]
        try:
            return list(self._generate_locations(browser))
        finally:
            self.b.switch_page(current_page, context=SelectionType.ALL, browser=SelectionType.ALL)

    def _generate_titles(self, browser: str):
        for page_id in self._get_page_ids(browser):
            self.b.switch_page(page_id, context=SelectionType.ALL, browser=SelectionType.ALL)
            yield self.b.get_title()

    @keyword(tags=("IMPLEMENTED",))
    def go_back(self):
        self.b.go_back()

    @keyword(tags=("IMPLEMENTED",))
    def go_to(self, url):
        self.b.go_to(url)

    @keyword
    def handle_alert(self, action: str = "ACCEPT", timeout: Optional[timedelta] = None):
        "*NOT IMPLEMENTED YET*"
        raise NotImplementedError("keyword is not implemented")

    @keyword(tags=("IMPLEMENTED",))
    def input_password(self, locator: WebElement, password: str, clear: bool = True):
        org_level = BuiltIn().set_log_level(level="NONE")
        try:
            self.input_text(locator, password, clear)
        finally:
            BuiltIn().set_log_level(level=org_level)

    @keyword(tags=("IMPLEMENTED",))
    def input_text(self, locator: WebElement, text: str, clear: bool = True):
        self.b.type_text(locator, text, clear=clear)

    @keyword
    def input_text_into_alert(
        self, text: str, action: str = "ACCEPT", timeout: Optional[timedelta] = None
    ):
        "*NOT IMPLEMENTED YET*"
        raise NotImplementedError("keyword is not implemented")

    @keyword(tags=("IMPLEMENTED",))
    def list_selection_should_be(self, locator: WebElement, *expected: str):
        selected_labels = self.b.get_selected_options(locator, SelectAttribute.label)
        selected_values = self.b.get_selected_options(locator, SelectAttribute.value)
        assert sorted(selected_labels) == sorted(expected) or sorted(selected_values) == sorted(
            expected
        ), f"Expected selection to be {expected}, but was {selected_labels} ({selected_values})"

    @keyword(tags=("IMPLEMENTED",))
    def list_should_have_no_selections(self, locator: WebElement):
        self.b.get_selected_options(locator, SelectAttribute.label, EQUALS)

    @keyword(tags=("IMPLEMENTED",))
    def location_should_be(self, url: str, message: Optional[str] = None):
        self.b.get_url(EQUALS, url, message)

    @keyword(tags=("IMPLEMENTED",))
    def location_should_contain(self, expected: str, message: Optional[str] = None):
        self.b.get_url(CONTAINS, expected, message)

    @keyword(tags=("IMPLEMENTED",))
    def log_location(self):
        location = self.b.get_url()
        logger.info(location)
        return location

    @keyword(tags=("IMPLEMENTED",))
    def log_source(self, loglevel: str = "INFO"):
        source = self.b.get_page_source()
        logger.write(source, level=loglevel)
        return source

    @keyword(tags=("IMPLEMENTED",))
    def log_title(self):
        title = self.b.get_title()
        logger.info(title)
        return title

    @keyword(tags=("IMPLEMENTED",))
    def maximize_browser_window(self):
        self.b.set_viewport_size(1920, 1080)

    @keyword(tags=("IMPLEMENTED",))
    def mouse_down(self, locator: WebElement):
        self.b.hover(locator)
        self.b.mouse_button(MouseButtonAction.down)

    @keyword(tags=("IMPLEMENTED",))
    def mouse_down_on_image(self, locator: WebElement):
        locator = self.get_image_locator(locator)
        self.mouse_down(locator)

    @keyword(tags=("IMPLEMENTED",))
    def mouse_down_on_link(self, locator: WebElement):
        locator = self.get_link_locator(locator)
        self.mouse_down(locator)

    @keyword(tags=("IMPLEMENTED",))
    def mouse_out(self, locator: WebElement):
        bbox = self.b.get_boundingbox(locator, BoundingBoxFields.ALL)
        self.b.hover(locator)
        self.b.mouse_move_relative_to(locator, bbox.width / 2 + 1, bbox.height / 2 + 1, steps=10)

    @keyword(tags=("IMPLEMENTED",))
    def mouse_over(self, locator: WebElement):
        self.b.hover(locator)

    @keyword(tags=("IMPLEMENTED",))
    def mouse_up(self, locator: WebElement):
        self.b.hover(locator)
        self.b.mouse_button(MouseButtonAction.up)

    @keyword(tags=("IMPLEMENTED",))
    def open_browser(
        self,
        url: Optional[str] = None,
        browser: str = "firefox",
        alias: Optional[str] = None,
        remote_url: Union[bool, str] = False,
        desired_capabilities: Union[dict, None, str] = None,
        ff_profile_dir: Optional[str] = None,
        options: Any = None,
        service_log_path: Optional[str] = None,
        executable_path: Optional[str] = None,
    ):
        browser_enum, headless = BROWSERS.get(browser, (SupportedBrowsers.chromium, False))
        ids = self.b.new_persistent_context(
            url=url, browser=browser_enum, args=options, headless=headless
        )
        identifier = str(next(self._browser_index))
        self._browser_indexes[identifier] = ids[0]
        if alias:
            self._browser_aliases[alias] = identifier
        return identifier

    @keyword(tags=("IMPLEMENTED",))
    def open_context_menu(self, locator: WebElement):
        self.b.click(locator, MouseButton.right)

    @keyword(tags=("IMPLEMENTED",))
    def page_should_contain(self, text: str, loglevel: str = "TRACE"):
        assert self.page_contains(f"text={text}"), f"Page should have contained text '{text}'"

    @keyword(tags=("IMPLEMENTED",))
    def page_should_contain_button(
        self,
        locator: WebElement,
        message: Optional[str] = None,
        loglevel: str = "TRACE",
    ):
        locator = self.get_button_locator(locator)
        for element in self.b.get_elements(locator):
            if self.b.get_property(element, "nodeName") in ["INPUT", "BUTTON"]:
                return
        self.log_source(loglevel)
        raise AssertionError(message or f"Page should have contained button '{locator}'")

    @keyword(tags=("IMPLEMENTED",))
    def page_should_contain_checkbox(
        self,
        locator: WebElement,
        message: Optional[str] = None,
        loglevel: str = "TRACE",
    ):
        elements = self.b.get_elements(locator)
        for element in elements:
            if (
                self.b.get_attribute(element, "type").lower() == "checkbox"
                and self.b.get_property(element, "nodeName") == "INPUT"
            ):
                return
        self.log_source(loglevel)
        raise AssertionError(message or f"Page should have contained checkbox '{locator}'")

    @keyword(tags=("IMPLEMENTED",))
    def page_should_contain_element(
        self,
        locator: WebElement,
        message: Optional[str] = None,
        loglevel: str = "TRACE",
        limit: Optional[int] = None,
    ):
        count = self.b.get_element_count(locator)
        if limit is not None:
            if count == limit:
                return
            self.log_source(loglevel)
            raise AssertionError(
                message
                or f"Page should have contained {limit} element(s), "
                f"but it did contained {count} element(s)"
            )
        if not count:
            self.log_source(loglevel)
            raise AssertionError(message or f"Page should have contained element '{locator}'")

    @keyword(tags=("IMPLEMENTED",))
    def page_should_contain_image(
        self,
        locator: WebElement,
        message: Optional[str] = None,
        loglevel: str = "TRACE",
    ):
        locator = self.get_image_locator(locator)
        for element in self.b.get_elements(locator):
            if self.b.get_property(element, "nodeName") == "IMG":
                return
        self.log_source(loglevel)
        raise AssertionError(message or f"Page should have contained image '{locator}'")

    @keyword(tags=("IMPLEMENTED",))
    def page_should_contain_link(
        self,
        locator: WebElement,
        message: Optional[str] = None,
        loglevel: str = "TRACE",
    ):
        locator = self.get_link_locator(locator)
        for element in self.b.get_elements(locator):
            if self.b.get_property(element, "nodeName") == "A":
                return
        self.log_source(loglevel)
        raise AssertionError(message or f"Page should have contained link '{locator}'")

    @keyword(tags=("IMPLEMENTED",))
    def page_should_contain_list(
        self,
        locator: WebElement,
        message: Optional[str] = None,
        loglevel: str = "TRACE",
    ):
        for element in self.b.get_elements(locator):
            if self.b.get_property(element, "nodeName") == "SELECT":
                return
        self.log_source(loglevel)
        raise AssertionError(message or f"Page should have contained list '{locator}'")

    @keyword(tags=("IMPLEMENTED",))
    def page_should_contain_radio_button(
        self,
        locator: WebElement,
        message: Optional[str] = None,
        loglevel: str = "TRACE",
    ):
        for element in self.b.get_elements(locator):
            if (
                self.b.get_attribute(element, "type").lower() == "radio"
                and self.b.get_property(element, "nodeName") == "INPUT"
            ):
                return
        self.log_source(loglevel)
        raise AssertionError(message or f"Page should have contained radio button '{locator}'")

    @keyword(tags=("IMPLEMENTED",))
    def page_should_contain_textfield(
        self,
        locator: WebElement,
        message: Optional[str] = None,
        loglevel: str = "TRACE",
    ):
        for element in self.b.get_elements(locator):
            if self.b.get_property(element, "nodeName") == "INPUT" and self.b.get_attribute(
                element, "type"
            ).lower() in [
                "date",
                "datetime-local",
                "email",
                "month",
                "number",
                "password",
                "search",
                "tel",
                "text",
                "time",
                "url",
                "week",
                "file",
            ]:
                return
        self.log_source(loglevel)
        raise AssertionError(message or f"Page should have contained textfield '{locator}'")

    @keyword(tags=("IMPLEMENTED",))
    def page_should_not_contain(self, text: str, loglevel: str = "TRACE"):
        try:
            assert not self.page_contains(
                f"text={text}"
            ), f"Page should have not contained text '{text}'"
        except AssertionError as e:
            self.log_source(loglevel)
            raise e

    @keyword(tags=("IMPLEMENTED",))
    def page_should_not_contain_button(
        self,
        locator: WebElement,
        message: Optional[str] = None,
        loglevel: str = "TRACE",
    ):
        locator = self.get_button_locator(locator)
        for element in self.b.get_elements(locator):
            if self.b.get_property(element, "nodeName") in ["INPUT", "BUTTON"]:
                self.log_source(loglevel)
                raise AssertionError(
                    message or f"Page should have not contained button '{locator}'"
                )

    @keyword(tags=("IMPLEMENTED",))
    def page_should_not_contain_checkbox(
        self,
        locator: WebElement,
        message: Optional[str] = None,
        loglevel: str = "TRACE",
    ):
        for element in self.b.get_elements(locator):
            if (
                self.b.get_attribute(element, "type").lower() == "checkbox"
                and self.b.get_property(element, "nodeName") == "INPUT"
            ):
                self.log_source(loglevel)
                raise AssertionError(
                    message or f"Page should have not contained checkbox '{locator}'"
                )

    @keyword(tags=("IMPLEMENTED",))
    def page_should_not_contain_element(
        self,
        locator: WebElement,
        message: Optional[str] = None,
        loglevel: str = "TRACE",
    ):
        if self.b.get_element_count(locator):
            self.log_source(loglevel)
            raise AssertionError(message or f"Page should have not contained element '{locator}'")

    @keyword(tags=("IMPLEMENTED",))
    def page_should_not_contain_image(
        self,
        locator: WebElement,
        message: Optional[str] = None,
        loglevel: str = "TRACE",
    ):
        locator = self.get_image_locator(locator)
        for element in self.b.get_elements(locator):
            if self.b.get_property(element, "nodeName") == "IMG":
                self.log_source(loglevel)
                raise AssertionError(message or f"Page should have not contained image '{locator}'")

    @keyword(tags=("IMPLEMENTED",))
    def page_should_not_contain_link(
        self,
        locator: WebElement,
        message: Optional[str] = None,
        loglevel: str = "TRACE",
    ):
        locator = self.get_link_locator(locator)
        for element in self.b.get_elements(locator):
            if self.b.get_property(element, "nodeName") == "A":
                self.log_source(loglevel)
                raise AssertionError(message or f"Page should have not contained link '{locator}'")

    @keyword(tags=("IMPLEMENTED",))
    def page_should_not_contain_list(
        self,
        locator: WebElement,
        message: Optional[str] = None,
        loglevel: str = "TRACE",
    ):
        for element in self.b.get_elements(locator):
            if self.b.get_property(element, "nodeName") == "SELECT":
                self.log_source(loglevel)
                raise AssertionError(message or f"Page should have not contained list '{locator}'")

    @keyword(tags=("IMPLEMENTED",))
    def page_should_not_contain_radio_button(
        self,
        locator: WebElement,
        message: Optional[str] = None,
        loglevel: str = "TRACE",
    ):
        for element in self.b.get_elements(locator):
            if (
                self.b.get_attribute(element, "type").lower() == "radio"
                and self.b.get_property(element, "nodeName") == "INPUT"
            ):
                self.log_source(loglevel)
                raise AssertionError(
                    message or f"Page should have not contained radio button '{locator}'"
                )

    @keyword(tags=("IMPLEMENTED",))
    def page_should_not_contain_textfield(
        self,
        locator: WebElement,
        message: Optional[str] = None,
        loglevel: str = "TRACE",
    ):
        for element in self.b.get_elements(locator):
            if self.b.get_property(element, "nodeName") == "INPUT" and self.b.get_attribute(
                element, "type"
            ).lower() in [
                "date",
                "datetime-local",
                "email",
                "month",
                "number",
                "password",
                "search",
                "tel",
                "text",
                "time",
                "url",
                "week",
                "file",
            ]:
                self.log_source(loglevel)
                raise AssertionError(
                    message or f"Page should have not contained textfield '{locator}'"
                )

    @keyword
    def press_key(self, locator: WebElement, key: str):
        "*DEPRECATED*"
        raise NotImplementedError("keyword is not implemented")

    @keyword
    def press_keys(self, locator: Optional[WebElement] = None, *keys: str):
        "*NOT IMPLEMENTED YET*"
        raise NotImplementedError("keyword is not implemented")

    @keyword(tags=("IMPLEMENTED",))
    def radio_button_should_be_set_to(self, group_name: str, value: str):
        radios = self.b.get_elements(f"css=input[type='radio'][name='{group_name}']")
        actual_value = None
        for radio in radios:
            if self.b.get_checkbox_state(radio):
                actual_value = self.b.get_attribute(radio, "value")
                break
        if actual_value is None or actual_value != value:
            raise AssertionError(
                f"Selection of radio button '{group_name}' should have "
                f"been '{value}' but was '{actual_value}'."
            )

    @keyword(tags=("IMPLEMENTED",))
    def radio_button_should_not_be_selected(self, group_name: str):
        radios = self.b.get_elements(f"css=input[type='radio'][name='{group_name}']")
        actual_value = None
        for radio in radios:
            if self.b.get_checkbox_state(radio):
                actual_value = self.b.get_attribute(radio, "value")
                break
        if actual_value is not None:
            raise AssertionError(
                f"Radio button group '{group_name}' should not have "
                f"had selection, but '{actual_value}' was selected."
            )

    @keyword
    def register_keyword_to_run_on_failure(self, keyword: Optional[str]):
        "*NOT IMPLEMENTED YET*"
        raise NotImplementedError("keyword is not implemented")

    @keyword(tags=("IMPLEMENTED",))
    def reload_page(self):
        self.b.reload()

    @keyword
    def remove_location_strategy(self, strategy_name: str):
        "*NOT IMPLEMENTED YET*"
        raise NotImplementedError("keyword is not implemented")

    @keyword(tags=("IMPLEMENTED",))
    def scroll_element_into_view(self, locator: WebElement):
        self.b.scroll_to_element(locator)

    @keyword(tags=("IMPLEMENTED",))
    def select_all_from_list(self, locator: WebElement):
        if not self.b.get_property(locator, "multiple"):
            raise RuntimeError("'Select All From List' works only with multi-selection lists.")
        options = [item["value"] for item in self.b.get_select_options(locator)]
        self.b.select_options_by(locator, SelectAttribute.value, *options)

    @keyword(tags=("IMPLEMENTED",))
    def select_checkbox(self, locator: WebElement):
        if not (
            self.b.get_attribute(locator, "type").lower() == "checkbox"
            and self.b.get_property(locator, "nodeName") == "INPUT"
        ):
            raise RuntimeError("'Select Checkbox' works only with checkboxes.")
        self.b.check_checkbox(locator)

    @keyword(tags=("IMPLEMENTED",))
    def select_frame(self, locator: WebElement):
        self.b.set_selector_prefix(f"{locator} >>>", scope=Scope.Global)

    @keyword(tags=("IMPLEMENTED",))
    def select_from_list_by_index(self, locator: WebElement, *indexes: str):
        if self.b.get_property(locator, "multiple"):
            selection = self.b.get_selected_options(locator, SelectAttribute.index)
            indexes = [*indexes, *selection]
        self.b.select_options_by(locator, SelectAttribute.index, *indexes)

    @keyword(tags=("IMPLEMENTED",))
    def select_from_list_by_label(self, locator: WebElement, *labels: str):
        if self.b.get_property(locator, "multiple"):
            selection = self.b.get_selected_options(locator, SelectAttribute.label)
            labels = [*labels, *selection]
        self.b.select_options_by(locator, SelectAttribute.label, *labels)

    @keyword(tags=("IMPLEMENTED",))
    def select_from_list_by_value(self, locator: WebElement, *values: str):
        if self.b.get_property(locator, "multiple"):
            selection = self.b.get_selected_options(locator, SelectAttribute.value)
            values = [*values, *selection]
        self.b.select_options_by(locator, SelectAttribute.value, *values)

    @keyword(tags=("IMPLEMENTED",))
    def select_radio_button(self, group_name: str, value: str):
        selector = (
            f"input[type='radio'][name='{group_name}'][value='{value}'],"
            f"input[type='radio'][name='{group_name}']#{value}"
        )
        self.b.check_checkbox(selector)

    @keyword
    def set_browser_implicit_wait(self, value: timedelta):
        "*NOT IMPLEMENTED YET*"
        raise NotImplementedError("keyword is not implemented")

    @keyword(tags=("IMPLEMENTED",))
    def set_focus_to_element(self, locator: WebElement):
        self.b.focus(locator)

    @keyword
    def set_screenshot_directory(self, path: Optional[str]):
        "*NOT IMPLEMENTED YET*"
        raise NotImplementedError("keyword is not implemented")

    @keyword(tags=("IMPLEMENTED",))
    def set_selenium_implicit_wait(self, value: timedelta):
        self.b.set_browser_timeout(value)

    @keyword
    def set_selenium_speed(self, value: timedelta):
        "*NOT IMPLEMENTED YET*"
        raise NotImplementedError("keyword is not implemented")

    @keyword(tags=("IMPLEMENTED",))
    def set_selenium_timeout(self, value: timedelta):
        return self.b.set_browser_timeout(value)

    @keyword
    def set_window_position(self, x: int, y: int):
        "*NOT IMPLEMENTED YET*"
        raise NotImplementedError("keyword is not implemented")

    @keyword(tags=("IMPLEMENTED",))
    def set_window_size(self, width: int, height: int, inner: bool = False):
        self.b.set_viewport_size(width, height)

    @keyword
    def simulate_event(self, locator: WebElement, event: str):
        "*NOT IMPLEMENTED YET*"
        raise NotImplementedError("keyword is not implemented")

    @keyword
    def submit_form(self, locator: Optional[WebElement] = None):
        "*NOT IMPLEMENTED YET*"
        raise NotImplementedError("keyword is not implemented")

    @keyword(tags=("IMPLEMENTED",))
    def switch_browser(self, index_or_alias: str):
        id = self._browser_indexes.get(index_or_alias, None) or self._browser_indexes.get(
            self._browser_aliases.get(index_or_alias), None
        )
        if id is None:
            raise ValueError(f"Browser '{index_or_alias}' not found")
        return self.b.switch_browser(id)

    @keyword
    def switch_window(
        self,
        locator: Union[list, str] = "MAIN",
        timeout: Optional[str] = None,
        browser: str = "CURRENT",
    ):
        "*NOT IMPLEMENTED YET*"
        raise NotImplementedError("keyword is not implemented")

    @keyword
    def table_cell_should_contain(
        self,
        locator: Optional[WebElement],
        row: int,
        column: int,
        expected: str,
        loglevel: str = "TRACE",
    ):
        "*NOT IMPLEMENTED YET*"
        raise NotImplementedError("keyword is not implemented")

    @keyword
    def table_column_should_contain(
        self,
        locator: Optional[WebElement],
        column: int,
        expected: str,
        loglevel: str = "TRACE",
    ):
        "*NOT IMPLEMENTED YET*"
        raise NotImplementedError("keyword is not implemented")

    @keyword
    def table_footer_should_contain(
        self,
        locator: Optional[WebElement],
        expected: str,
        loglevel: str = "TRACE",
    ):
        "*NOT IMPLEMENTED YET*"
        raise NotImplementedError("keyword is not implemented")

    @keyword
    def table_header_should_contain(
        self,
        locator: Optional[WebElement],
        expected: str,
        loglevel: str = "TRACE",
    ):
        "*NOT IMPLEMENTED YET*"
        raise NotImplementedError("keyword is not implemented")

    @keyword
    def table_row_should_contain(
        self,
        locator: Optional[WebElement],
        row: int,
        expected: str,
        loglevel: str = "TRACE",
    ):
        "*NOT IMPLEMENTED YET*"
        raise NotImplementedError("keyword is not implemented")

    @keyword
    def table_should_contain(
        self,
        locator: Optional[WebElement],
        expected: str,
        loglevel: str = "TRACE",
    ):
        "*NOT IMPLEMENTED YET*"
        raise NotImplementedError("keyword is not implemented")

    @keyword(tags=("IMPLEMENTED",))
    def textarea_should_contain(
        self,
        locator: WebElement,
        expected: str,
        message: Optional[str] = None,
    ):
        for element in self.b.get_elements(locator):
            if self.b.get_property(element, "nodeName") == "TEXTAREA":
                self.b.get_text(locator, CONTAINS, expected, message)
                return
        raise AssertionError("Element is not a textarea")

    @keyword(tags=("IMPLEMENTED",))
    def textarea_value_should_be(
        self,
        locator: WebElement,
        expected: str,
        message: Optional[str] = None,
    ):
        for element in self.b.get_elements(locator):
            if self.b.get_property(element, "nodeName") == "TEXTAREA":
                self.b.get_text(locator, EQUALS, expected, message)
                return
        raise AssertionError("Element is not a textarea")

    @keyword(tags=("IMPLEMENTED",))
    def textfield_should_contain(
        self,
        locator: WebElement,
        expected: str,
        message: Optional[str] = None,
    ):
        for element in self.b.get_elements(locator):
            if self.b.get_property(element, "nodeName") == "INPUT" and self.b.get_attribute(
                element, "type"
            ).lower() in [
                "date",
                "datetime-local",
                "email",
                "month",
                "number",
                "password",
                "search",
                "tel",
                "text",
                "time",
                "url",
                "week",
                "file",
            ]:
                self.b.get_text(locator, CONTAINS, expected, message)
                return
        raise AssertionError("Element is not a textfield")

    @keyword(tags=("IMPLEMENTED",))
    def textfield_value_should_be(
        self,
        locator: WebElement,
        expected: str,
        message: Optional[str] = None,
    ):
        for element in self.b.get_elements(locator):
            if self.b.get_property(element, "nodeName") == "INPUT" and self.b.get_attribute(
                element, "type"
            ).lower() in [
                "date",
                "datetime-local",
                "email",
                "month",
                "number",
                "password",
                "search",
                "tel",
                "text",
                "time",
                "url",
                "week",
                "file",
            ]:
                self.b.get_text(locator, EQUALS, expected, message)
                return
        raise AssertionError("Element is not a textfield")

    @keyword(tags=("IMPLEMENTED",))
    def title_should_be(self, title: str, message: Optional[str] = None):
        self.b.get_title(EQUALS, title, message)

    @keyword(tags=("IMPLEMENTED",))
    def unselect_all_from_list(self, locator: WebElement):
        if not self.b.get_property(locator, "multiple"):
            raise RuntimeError("Un-selecting options works only with multi-selection lists.")
        self.b.select_options_by(locator, SelectAttribute.index)

    @keyword(tags=("IMPLEMENTED",))
    def unselect_checkbox(self, locator: WebElement):
        if not (
            self.b.get_attribute(locator, "type").lower() == "checkbox"
            and self.b.get_property(locator, "nodeName") == "INPUT"
        ):
            raise AssertionError("Element is not a checkbox")
        self.b.uncheck_checkbox(locator)

    @keyword(tags=("IMPLEMENTED",))
    def unselect_frame(self):
        self.b.set_selector_prefix("", scope=Scope.Global)

    @keyword(tags=("IMPLEMENTED",))
    def unselect_from_list_by_index(self, locator: WebElement, *indexes: str):
        if not indexes:
            raise ValueError("No indexes given.")
        if not self.b.get_property(locator, "multiple"):
            raise RuntimeError("Un-selecting options works only with multi-selection lists.")
        selection = self.b.get_selected_options(locator, SelectAttribute.index)
        self.b.select_options_by(
            locator, SelectAttribute.index, *[s for s in selection if s not in indexes]
        )

    @keyword(tags=("IMPLEMENTED",))
    def unselect_from_list_by_label(self, locator: WebElement, *labels: str):
        if not labels:
            raise ValueError("No labels given.")
        if not self.b.get_property(locator, "multiple"):
            raise RuntimeError("Un-selecting options works only with multi-selection lists.")
        selection = self.b.get_selected_options(locator, SelectAttribute.label)
        self.b.select_options_by(
            locator, SelectAttribute.label, *[s for s in selection if s not in labels]
        )

    @keyword(tags=("IMPLEMENTED",))
    def unselect_from_list_by_value(self, locator: WebElement, *values: str):
        if not values:
            raise ValueError("No values given.")
        if not self.b.get_property(locator, "multiple"):
            raise RuntimeError("Un-selecting options works only with multi-selection lists.")
        selection = self.b.get_selected_options(locator, SelectAttribute.value)
        self.b.select_options_by(
            locator, SelectAttribute.value, *[s for s in selection if s not in values]
        )

    @keyword
    def wait_for_condition(
        self,
        condition: str,
        timeout: Optional[timedelta] = None,
        error: Optional[str] = None,
    ):
        "*NOT IMPLEMENTED YET*"
        raise NotImplementedError("keyword is not implemented")

    @keyword(tags=("IMPLEMENTED",))
    def wait_until_element_contains(
        self,
        locator: Optional[WebElement],
        text: str,
        timeout: Optional[timedelta] = None,
        error: Optional[str] = None,
    ):
        self._wait_until(
            lambda: text in self.b.get_text(locator),
            f"Element '{locator}' did not get text '{text}' in <TIMEOUT>.",
            timeout,
            error,
        )

    @keyword(tags=("IMPLEMENTED",))
    def wait_until_element_does_not_contain(
        self,
        locator: Optional[WebElement],
        text: str,
        timeout: Optional[timedelta] = None,
        error: Optional[str] = None,
    ):
        self._wait_until(
            lambda: text not in self.b.get_text(locator),
            f"Element '{locator}' still had text '{text}' after <TIMEOUT>.",
            timeout,
            error,
        )

    @keyword(tags=("IMPLEMENTED",))
    def wait_until_element_is_enabled(
        self,
        locator: Optional[WebElement],
        timeout: Optional[timedelta] = None,
        error: Optional[str] = None,
    ):
        self.b.wait_for_condition(
            ConditionInputs.element_states,
            locator,
            VALIDATE,
            "not bool((readonly | disabled) & value)",
            timeout=timeout,
            message=error,
        )

    @keyword(tags=("IMPLEMENTED",))
    def wait_until_element_is_not_visible(
        self,
        locator: Optional[WebElement],
        timeout: Optional[timedelta] = None,
        error: Optional[str] = None,
    ):
        self.b.wait_for_condition(
            ConditionInputs.element_states,
            locator,
            NOT_CONTAINS,
            "visible",
            timeout=timeout,
            message=error,
        )

    @keyword(tags=("IMPLEMENTED",))
    def wait_until_element_is_visible(
        self,
        locator: Optional[WebElement],
        timeout: Optional[timedelta] = None,
        error: Optional[str] = None,
    ):
        self.b.wait_for_condition(
            ConditionInputs.element_states,
            locator,
            CONTAINS,
            "visible",
            timeout=timeout,
            message=error,
        )

    @keyword(tags=("IMPLEMENTED",))
    def wait_until_location_contains(
        self,
        expected: str,
        timeout: Optional[timedelta] = None,
        message: Optional[str] = None,
    ):
        self.b.wait_for_function(
            f"() => window.location.href.includes(`{expected}`)", timeout=timeout, message=message
        )

    @keyword(tags=("IMPLEMENTED",))
    def wait_until_location_does_not_contain(
        self,
        location: str,
        timeout: Optional[timedelta] = None,
        message: Optional[str] = None,
    ):
        self.b.wait_for_function(
            f"() => !window.location.href.includes(`{location}`)", timeout=timeout, message=message
        )

    @keyword(tags=("IMPLEMENTED",))
    def wait_until_location_is(
        self,
        expected: str,
        timeout: Optional[timedelta] = None,
        message: Optional[str] = None,
    ):
        self.b.wait_for_function(
            f"() => window.location.href === `{expected}`", timeout=timeout, message=message
        )

    @keyword(tags=("IMPLEMENTED",))
    def wait_until_location_is_not(
        self,
        location: str,
        timeout: Optional[timedelta] = None,
        message: Optional[str] = None,
    ):
        self.b.wait_for_function(
            f"() => window.location.href !== `{location}`", timeout=timeout, message=message
        )

    @keyword(tags=("IMPLEMENTED",))
    def wait_until_page_contains(
        self,
        text: str,
        timeout: Optional[timedelta] = None,
        error: Optional[str] = None,
    ):
        self._wait_until(
            lambda: self.page_contains(f"text={text}"),
            f"Text '{text}' did not appear in <TIMEOUT>.",
            timeout,
            error,
        )

    @keyword(tags=("IMPLEMENTED",))
    def wait_until_page_contains_element(
        self,
        locator: Optional[WebElement],
        timeout: Optional[timedelta] = None,
        error: Optional[str] = None,
        limit: Optional[int] = None,
    ):
        if limit is None:
            op = GREATER_THAN
            limit = 0
        else:
            op = EQUALS
        self.b.wait_for_condition(
            ConditionInputs.element_count,
            locator,
            op,
            limit,
            timeout=timeout,
            message=error or f"Element '{locator}' did not appear in <TIMEOUT>.",
        )

    @keyword(tags=("IMPLEMENTED",))
    def wait_until_page_does_not_contain(
        self,
        text: str,
        timeout: Optional[timedelta] = None,
        error: Optional[str] = None,
    ):
        self._wait_until(
            lambda: not self.page_contains(f"text={text}"),
            f"Text '{text}' did not disappear in <TIMEOUT>.",
            timeout,
            error,
        )

    @keyword(tags=("IMPLEMENTED",))
    def wait_until_page_does_not_contain_element(
        self,
        locator: Optional[WebElement],
        timeout: Optional[timedelta] = None,
        error: Optional[str] = None,
        limit: Optional[int] = None,
    ):
        if limit is None:
            operator = EQUALS
            limit = 0
        else:
            operator = NOT_EQUALS
        self.b.wait_for_condition(
            ConditionInputs.element_count,
            locator,
            operator,
            limit,
            timeout=timeout,
            message=error or f"Element '{locator}' did not appear in <TIMEOUT>.",
        )

    def _wait_until(self, condition, error, timeout: timedelta = None, custom_error=None):
        timeout = self.b.get_timeout(timeout) / 1000
        if custom_error is None:
            error = error.replace("<TIMEOUT>", secs_to_timestr(timeout))
        else:
            error = custom_error
        self._wait_until_worker(condition, timeout, error)

    def _wait_until_worker(self, condition, timeout, error):
        max_time = time.time() + timeout
        not_found = None
        while time.time() < max_time:
            try:
                if condition():
                    return
            except Exception as err:
                not_found = str(err)
            else:
                not_found = None
            time.sleep(0.2)
        raise AssertionError(not_found or error)
