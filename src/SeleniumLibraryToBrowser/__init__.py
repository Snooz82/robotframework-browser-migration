import re
import time
from collections import namedtuple
from datetime import datetime, timedelta, timezone
from itertools import count
from pathlib import Path
from typing import Any, Generator, List, Optional, Union

from robot.api import SkipExecution, logger
from robot.api.deco import library
from robot.libraries.BuiltIn import BuiltIn, RobotNotRunningError
from robot.libraries.DateTime import convert_date
from robot.result.model import Message
from robot.result.model import TestCase as ResultTestCase
from robot.running import EXECUTION_CONTEXTS
from robot.running.model import TestCase
from robot.utils import DotDict, secs_to_timestr, timestr_to_secs
from robotlibcore import DynamicCore, keyword

from Browser import Browser, SupportedBrowsers
from Browser.assertion_engine import AssertionOperator as AO
from Browser.base import LibraryComponent
from Browser.generated.playwright_pb2 import Request
from Browser.utils.data_types import (
    AutoClosingLevel,
    BoundingBoxFields,
    CookieType,
    ElementState,
    KeyAction,
    KeyboardInputAction,
    MouseButton,
    MouseButtonAction,
    Scope,
    SelectAttribute,
    SelectionType,
)
from SeleniumLibraryToBrowser.keys import Keys

from .errors import (
    CookieNotFound,
    ElementNotFound,
    InvalidArgumentException,
    NoSuchElementException,
    NoSuchFrameException,
    WindowNotFound,
)

try:
    from SeleniumLibrary import SeleniumLibrary
except ImportError:
    SeleniumLibrary = None


EQUALS = AO["=="]
NOT_EQUALS = AO["!="]
CONTAINS = AO["*="]
NOT_CONTAINS = AO["not contains"]
STARTS_WITH = AO["^="]
ENDS_WITH = AO["$="]
THEN = AO["then"]
VALIDATE = AO["validate"]
GREATER_THAN = AO[">"]

DEFAULT_FILENAME_PAGE = "selenium-screenshot-{index}.png"
DEFAULT_FILENAME_ELEMENT = "selenium-element-screenshot-{index}.png"
EMBED = "EMBED"


__version__ = "0.8.0"


class CookieInformation:
    def __init__(
        self,
        name,
        value,
        path=None,
        domain=None,
        secure=False,
        httpOnly: bool = False,
        expires: Optional[datetime] = None,
        **extra,
    ):
        self.name: str = name
        self.value: str = value
        self.path: str = path
        self.domain: str = domain
        self.secure: str = secure
        self.httpOnly: bool = httpOnly
        self.expiry: datetime = (
            expires.replace(tzinfo=timezone.utc).astimezone(tz=None).replace(tzinfo=None)
            if expires is not None
            else None
        )
        self.extra = extra

    def __str__(self):
        items = "name value path domain secure httpOnly expiry".split()
        string = "\n".join(f"{item}={getattr(self, item)}" for item in items)
        if self.extra:
            string = f"{string}\nextra={self.extra}\n"
        return string


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
        "default": "css=[id={loc}], [name={loc}]",
        "text": "text={loc}",
        "element": "element={loc}",
    }
    original_locator: Union[str, tuple] = ""

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
                new_locator = cls(selector.format(loc=loc))
                new_locator.original_locator = locator
                return new_locator
        if re.match(r"\(*//", locator):
            new_locator = cls(f"xpath={locator}")
            new_locator.original_locator = locator
            return new_locator
        new_locator = cls(f"[id='{locator}'], [name='{locator}']")
        new_locator.original_locator = locator
        return new_locator

    @staticmethod
    def is_default(locator: str):
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


class V3Listener:
    ROBOT_LISTENER_API_VERSION = 3

    def __init__(self, library):
        self.library = library
        self.depr = False

    def start_test(self, _test: TestCase, _result: ResultTestCase):
        self.depr = False

    def end_test(self, _test: TestCase, result: ResultTestCase):
        if self.depr and BuiltIn()._context.dry_run:
            result.status = "SKIP"

    def log_message(self, message: Message):
        if (
            message.level == "WARN"
            and "is deprecated" in message.message
            and BuiltIn()._context.dry_run
        ):
            self.depr = True


@library(converters={WebElement: WebElement.from_string})
class SeleniumLibraryToBrowser(DynamicCore):
    """General library documentation."""

    ROBOT_LIBRARY_SCOPE = "GLOBAL"
    ROBOT_LIBRARY_VERSION = __version__

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
        """Library init doc."""
        sl2b = SLtoB(
            timeout=timeout,
            implicit_wait=implicit_wait,
            run_on_failure=run_on_failure,
            screenshot_root_directory=screenshot_root_directory,
            plugins=plugins,
            event_firing_webdriver=event_firing_webdriver,
            browser_args=browser_args,
        )
        components = [sl2b]
        super().__init__(components)
        self.sl = SeleniumLibrary() if SeleniumLibrary else None

    @property
    def dry_run(self):
        ctx = EXECUTION_CONTEXTS.current
        return ctx.dry_run if ctx else False

    def keyword_implemented(self, name):
        return "IMPLEMENTED" in self.get_keyword_tags(name)

    def run_keyword(self, name, args, kwargs=None):
        if not self.keyword_implemented(name):
            raise SkipExecution(f"Keyword '{name.replace('_', ' ').title() }' is not implemented")
        return super().run_keyword(name, args, kwargs)

    def get_keyword_names(self):
        if self.dry_run:
            return [kw for kw in super().get_keyword_names() if self.keyword_implemented(kw)]
        return super().get_keyword_names()

    def get_keyword_documentation(self, name):
        if name == "__intro__":
            return self.__doc__
        if name == "__init__":
            return self.__init__.__doc__
        if not EXECUTION_CONTEXTS.current and not self.keyword_implemented(name):
            return "*DEPRECATED* keyword is not implemented yet."
        if not self.keyword_implemented(name):
            return "KEYWORD IS NOT YET IMPLEMENTED."
        try:
            name = getattr(self.sl, name).robot_name or name
            return self.sl.get_keyword_documentation(name)
        except:
            pass
        return super().get_keyword_documentation(name)


class SLtoB:
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
        self._browser_page_catalog = {}

    @property
    def b(self) -> Browser:
        if self._browser is None:
            # BuiltIn().import_library(name="Browser", *self._browser_args)
            try:
                self._browser = BuiltIn().get_library_instance("Browser")
            except Exception:
                self._browser = Browser(*self._browser_args)
            self._browser.set_strict_mode(False, Scope.Global)
            self._browser._auto_closing_level = AutoClosingLevel.MANUAL
            # BuiltIn().set_library_search_order("SeleniumLibraryToBrowser")
        return self._browser

    @property
    def library_comp(self) -> LibraryComponent:
        return LibraryComponent(self.b)

    @property
    def log_dir(self) -> Path:
        try:
            logfile = BuiltIn().get_variable_value("${LOG FILE}", None)
            if logfile is None or logfile == "NONE":
                return Path(BuiltIn().get_variable_value("${OUTPUTDIR}", Path.cwd()))
            return Path(logfile).parent
        except RobotNotRunningError:
            return Path.cwd()

    def get_button_locator(self, locator: WebElement) -> WebElement:
        original_locator = locator.original_locator
        loc = WebElement.is_default(locator)
        if loc:
            loc = loc.replace('"', '\\"')
            locator = WebElement(
                "xpath="
                f'//button[@id="{loc}"]|'
                f'//button[@name="{loc}"]|'
                f'//button[@value="{loc}"]|'
                f'//button[.="{loc}"]|'
                f'//input[@id="{loc}"]|'
                f'//input[@name="{loc}"]|'
                f'//input[@value="{loc}"]|'
                f'//input[@src="{loc}"]'
            )
            locator.original_locator = original_locator
        return locator

    def get_input_locator(self, locator: WebElement) -> WebElement:
        original_locator = locator.original_locator
        loc = WebElement.is_default(locator)
        if loc:
            loc = loc.replace('"', '\\"')
            locator = WebElement(
                "xpath="
                f'//input[@id="{loc}"]|'
                f'//input[@name="{loc}"]|'
                f'//input[@value="{loc}"]|'
                f'//input[@src="{loc}"]'
            )
            locator.original_locator = original_locator
        return locator

    def get_link_locator(self, locator: WebElement) -> WebElement:
        original_locator = locator.original_locator
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
            locator = WebElement(xpath.format(loc=loc))
            locator.original_locator = original_locator
        return locator

    def get_image_locator(self, locator: WebElement) -> WebElement:
        original_locator = locator.original_locator
        loc = WebElement.is_default(locator)
        if loc:
            locator = WebElement(
                f'xpath=//img[@id="{loc}"] | '
                f'//img[@name="{loc}"] | '
                f'//img[@src="{loc}"] | '
                f'//img[@alt="{loc}"]'
            )
            locator.original_locator = original_locator
        return locator

    def get_list_locator(self, locator: WebElement) -> WebElement:
        original_locator = locator.original_locator
        loc = WebElement.is_default(locator)
        if loc:
            locator = WebElement(
                f'xpath=//select[@id="{loc}"] | '
                f'//select[@name="{loc}"] | '
                f'//select[@value="{loc}"]'
            )
            locator.original_locator = original_locator
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

    def type_converter(self, argument: Any) -> str:
        return type(argument).__name__.lower()

    @keyword(tags=("IMPLEMENTED",))
    def add_cookie(
        self,
        name: str,
        value: str,
        path: str = "/",
        domain: Optional[str] = None,
        secure: bool = False,
        expiry: Union[None, int, str] = None,
    ):
        if domain is None:
            domain = self.b.evaluate_javascript(None, "window.location.hostname")
        if expiry is not None:
            expiry = self._expiry(expiry)
        self.b.add_cookie(name, value, domain=domain, path=path, secure=secure, expires=expiry)

    def _expiry(self, expiry):
        try:
            return int(expiry)
        except (ValueError, TypeError):
            return int(convert_date(expiry, result_format="epoch"))

    @keyword
    def add_location_strategy(
        self, strategy_name: str, strategy_keyword: str, persist: bool = False
    ):
        ...

    @keyword
    def alert_should_be_present(
        self,
        text: str = "",
        action: str = "ACCEPT",
        timeout: Optional[timedelta] = None,
    ):
        ...

    @keyword
    def alert_should_not_be_present(
        self, action: str = "ACCEPT", timeout: Optional[timedelta] = None
    ):
        ...

    @keyword(tags=("IMPLEMENTED",))
    def assign_id_to_element(self, locator: WebElement, id: str):
        self.b.evaluate_javascript(locator, f"element => element.id = '{id}'")

    @keyword(tags=("IMPLEMENTED",))
    def capture_element_screenshot(
        self,
        locator: WebElement,
        filename: str = DEFAULT_FILENAME_ELEMENT,
    ) -> str:
        if not self.b.get_page_ids():
            logger.info("Cannot capture screenshot from element because no browser is open.")
            return None
        try:
            self.b.get_element_states(locator, CONTAINS, "attached")
        except AssertionError:
            raise ElementNotFound(f"Element with locator '{locator.original_locator}' not found.")
        embedding = self._decide_embedded(filename)
        screenshot_file = (
            EMBED
            if embedding
            else re.sub(".png$", "", self._get_screenshot_path(filename, embedding))
        )
        screenshot_path = self.b.take_screenshot(filename=screenshot_file, selector=locator)
        return EMBED if embedding else screenshot_path

    @keyword(tags=("IMPLEMENTED",))
    def capture_page_screenshot(self, filename: str = DEFAULT_FILENAME_PAGE) -> str:
        if not self.b.get_page_ids():
            logger.info("Cannot capture screenshot from element because no browser is open.")
            return None
        embedding = self._decide_embedded(filename)
        screenshot_file = (
            EMBED
            if embedding
            else re.sub(".png$", "", self._get_screenshot_path(filename, embedding))
        )
        screenshot_path = self.b.take_screenshot(filename=screenshot_file)
        return EMBED if embedding else screenshot_path

    @keyword(tags=("IMPLEMENTED",))
    def checkbox_should_be_selected(self, locator: WebElement):
        logger.info(f"Verifying checkbox '{locator.original_locator}' is selected.")
        if not (
            self.b.get_attribute(locator, "type").lower() == "checkbox"
            and self.b.get_property(locator, "nodeName") == "INPUT"
        ):
            raise ElementNotFound(f"Checkbox with locator '{locator.original_locator}' not found.")
        try:
            self.b.get_checkbox_state(locator, EQUALS, True)
        except AssertionError as e:
            raise AssertionError(
                f"Checkbox '{locator.original_locator}' should have been selected but was not."
            ) from e

    @keyword(tags=("IMPLEMENTED",))
    def checkbox_should_not_be_selected(self, locator: WebElement):
        if not (
            self.b.get_attribute(locator, "type").lower() == "checkbox"
            and self.b.get_property(locator, "nodeName") == "INPUT"
        ):
            raise ElementNotFound(f"Checkbox with locator '{locator.original_locator}' not found.")
        try:
            self.b.get_checkbox_state(locator, EQUALS, False)
        except AssertionError as e:
            raise AssertionError(
                f"Checkbox '{locator.original_locator}' should not have been selected."
            ) from e

    @keyword(tags=("IMPLEMENTED",))
    def choose_file(self, locator: WebElement, file_path: str):
        file = Path(file_path).resolve()
        logger.info(f"Sending {file} to browser.")
        if not file.exists():
            raise InvalidArgumentException(f"Message: File not found: {file}")
        # self.b.upload_file_by_selector(locator, file_path)
        with self.b.playwright.grpc_channel() as stub:
            response = stub.UploadFileBySelector(
                Request().FileBySelector(
                    path=str(file),
                    selector=locator,
                    strict=self.library_comp.strict_mode,
                )
            )
            logger.debug(response.log)

    @keyword(tags=("IMPLEMENTED",))
    def clear_element_text(self, locator: WebElement):
        self.b.clear_text(locator)

    @keyword(tags=("IMPLEMENTED",))
    def click_button(self, locator: WebElement, modifier: Union[bool, str] = False):
        locator = self.get_button_locator(locator)
        self.click_element(locator, modifier)

    @keyword(tags=("IMPLEMENTED",))
    def click_element(
        self,
        locator: WebElement,
        modifier: Union[bool, str] = False,
        action_chain: bool = False,
    ):
        modifiers = []
        if modifier and modifier.upper() != "FALSE":
            logger.console(modifier)
            modifiers = modifier.split("+")
        else:
            logger.info(f"Clicking element '{locator.original_locator}'.")
        try:
            for mod in modifiers:
                if mod.upper() not in dict(Keys.__members__):
                    raise ValueError(f"'{mod.upper()}' modifier does not match to Selenium Keys")
                self.b.keyboard_key(KeyAction.down, Keys[mod.upper()].value)
            node = self.b.get_property(locator, "nodeName")
            if node == "OPTION":
                value = self.b.get_property(locator, "value")
                self.b.select_options_by(f"{locator} >> ..", SelectAttribute.value, value)
            else:
                self.b.click_with_options(locator, MouseButton.left)
        except ValueError as e:
            raise e
        except Exception as e:
            raise ElementNotFound(
                f"Element with locator '{locator.original_locator}' not found."
            ) from e
        finally:
            for mod in reversed(modifiers):
                try:
                    self.b.keyboard_key(KeyAction.up, Keys[mod.upper()].value)
                except:
                    pass

    @keyword(tags=("IMPLEMENTED",))
    def click_element_at_coordinates(self, locator: WebElement, xoffset: int, yoffset: int):
        bbox = self.b.get_boundingbox(selector=locator)  # {x, y, width, height}
        # calculates the half of the width and height of the element
        x = bbox["width"] / 2 + xoffset
        y = bbox["height"] / 2 + yoffset
        self.b.click_with_options(selector=locator, position_x=x, position_y=y)

    @keyword(tags=("IMPLEMENTED",))
    def click_image(self, locator: WebElement, modifier: Union[bool, str] = False):
        """See the Locating elements section for details about the locator syntax.
        When using the default locator strategy, images are searched using id, name, src and alt.
        """
        img_locator = self.get_image_locator(locator)
        try:
            self.b.get_element_count(img_locator, GREATER_THAN, 0)
            locator = img_locator
        except AssertionError as e:
            input_locator = self.get_input_locator(locator)
            try:
                self.b.get_element_count(input_locator, GREATER_THAN, 0)
                locator = input_locator
            except AssertionError:
                raise ElementNotFound(
                    f"Element with locator '{locator.original_locator}' not found."
                ) from e
        self.click_element(locator, modifier)

    @keyword(tags=("IMPLEMENTED",))
    def click_link(self, locator: WebElement, modifier: Union[bool, str] = False):
        """See the Locating elements section for details about the locator syntax.
        When using the default locator strategy, links are searched using id, name,
        href and the link text.
        """
        locator = self.get_link_locator(locator)
        self.click_element(locator, modifier)

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

    @keyword(tags=("IMPLEMENTED",))
    def cover_element(self, locator: WebElement):
        count = self.b.get_element_count(locator)
        if not count:
            raise ElementNotFound(f"No element with locator '{locator.original_locator}' found.")
        self.b.evaluate_javascript(
            locator,
            "elements => {",
            "    for (let old_element of elements) {"
            "       let newDiv = document.createElement('div');",
            "       newDiv.setAttribute('name', 'covered');",
            "       newDiv.style.backgroundColor = 'blue';",
            "       newDiv.style.zIndex = '999';",
            "       newDiv.style.top = old_element.offsetTop + 'px';",
            "       newDiv.style.left = old_element.offsetLeft + 'px';",
            "       newDiv.style.height = old_element.offsetHeight + 'px';",
            "       newDiv.style.width = old_element.offsetWidth + 'px';",
            "       old_element.parentNode.insertBefore(newDiv, old_element);",
            "       old_element.remove();",
            "       newDiv.parentNode.style.overflow = 'hidden';",
            "    }",
            "}",
            all_elements=True,
        )

    @keyword
    def create_webdriver(
        self, driver_name: str, alias: Optional[str] = None, kwargs=None, **init_kwargs
    ):
        ...

    @keyword(tags=("IMPLEMENTED",))
    def current_frame_should_contain(self, text: str, loglevel: str = "TRACE"):
        try:
            self.b.get_element_count(
                f"text=/.*{text}.*/",
                GREATER_THAN,
                0,
                f"Frame should have contained text '{text}' but did not.",
            )
        except AssertionError as e:
            self.log_source(loglevel)
            raise e
        logger.info(f"Current frame contains text '{text}'.")

    @keyword(tags=("IMPLEMENTED",))
    def current_frame_should_not_contain(self, text: str, loglevel: str = "TRACE"):
        try:
            self.b.get_element_count(
                f"text=/.*{text}.*/",
                EQUALS,
                0,
                f"Frame should not have contained text '{text}' but it did.",
            )
        except AssertionError as e:
            self.log_source(loglevel)
            raise e
        logger.info(f"Current frame did not contain text '{text}'.")

    @keyword(tags=("IMPLEMENTED",))
    def delete_all_cookies(self):
        self.b.delete_all_cookies()

    @keyword(tags=("IMPLEMENTED",))
    def delete_cookie(self, name):
        cookies = self.b.get_cookies()
        for cookie in cookies:
            if cookie.name == name:
                self.b.add_cookie(
                    cookie.name, cookie.value, expires=0, domain=cookie.domain, path=cookie.path
                )

    @keyword(tags=("IMPLEMENTED",))
    def double_click_element(self, locator: WebElement):
        logger.info(f"Double clicking element '{locator.original_locator}'.")
        try:
            self.b.click_with_options(locator, clickCount=2, delay=timedelta(milliseconds=100))
        except Exception as e:
            raise ElementNotFound(
                f"Element with locator '{locator.original_locator}' not found."
            ) from e

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
        attribute = self.get_element_attribute(locator, attribute)
        if attribute != expected:
            raise AssertionError(
                message
                or (
                    f"Element '{locator.original_locator}' attribute should have value '{expected}' "
                    f"({self.type_converter(expected)}) but its value was '{attribute}' "
                    f"({self.type_converter(attribute)})."
                )
            )

    @keyword(tags=("IMPLEMENTED",))
    def element_should_be_disabled(self, locator: WebElement):
        value = self.b.get_element_states(locator, return_names=False)
        if not (ElementState.readonly | ElementState.disabled) & value:
            raise AssertionError(f"Element '{locator.original_locator}' is enabled.")

    @keyword(tags=("IMPLEMENTED",))
    def element_should_be_enabled(self, locator: WebElement):
        value = self.b.get_element_states(locator, return_names=False)
        if (ElementState.readonly | ElementState.disabled) & value:
            raise AssertionError(f"Element '{locator.original_locator}' is disabled.")

    @keyword(tags=("IMPLEMENTED",))
    def element_should_be_focused(self, locator: WebElement):
        states = self.b.get_element_states(locator)
        if "attached" not in states:
            raise ElementNotFound(f"Element with locator '{locator.original_locator}' not found.")
        if "focused" not in states:
            raise AssertionError(f"Element '{locator.original_locator}' does not have focus.")

    @keyword(tags=("IMPLEMENTED",))
    def element_should_be_visible(self, locator: WebElement, message: Optional[str] = None):
        states = self.b.get_element_states(locator)
        if "visible" not in states:
            raise AssertionError(
                message
                or f"The element '{locator.original_locator}' should be visible, but it is not."
            )

    @keyword(tags=("IMPLEMENTED",))
    def element_should_contain(
        self,
        locator: WebElement,
        expected: Optional[str],
        message: Optional[str] = None,
        ignore_case: bool = False,
    ):
        try:
            value = self.b.get_text(locator)
        except Exception as e:
            raise ElementNotFound(
                f"Element with locator '{locator.original_locator}' not found."
            ) from e
        msg = (
            message
            or f"Element '{locator.original_locator}' should have contained text '{expected}' but its text was '{value}'."
        )
        if ignore_case:
            expected = expected.lower()
            value = value.lower()
        if expected not in value:
            raise AssertionError(msg)

    @keyword(tags=("IMPLEMENTED",))
    def element_should_not_be_visible(self, locator: WebElement, message: Optional[str] = None):
        states = self.b.get_element_states(locator)
        if "visible" in states:
            raise AssertionError(
                message
                or f"The element '{locator.original_locator}' should not be visible, but it is."
            )

    @keyword(tags=("IMPLEMENTED",))
    def element_should_not_contain(
        self,
        locator: WebElement,
        expected: Optional[str],
        message: Optional[str] = None,
        ignore_case: bool = False,
    ):
        msg = (
            message
            or f"Element '{locator.original_locator}' should not contain text '{expected}' but it did."
        )
        try:
            value = self.b.get_text(locator)
        except Exception as e:
            raise ElementNotFound(
                f"Element with locator '{locator.original_locator}' not found."
            ) from e
        if ignore_case:
            expected = expected.lower()
            value = value.lower()
        if expected in value:
            raise AssertionError(msg)

    @keyword(tags=("IMPLEMENTED",))
    def element_text_should_be(
        self,
        locator: WebElement,
        expected: Optional[str],
        message: Optional[str] = None,
        ignore_case: bool = False,
    ):
        value = self.b.get_text(locator)
        msg = (
            message
            or f"The text of element '{locator.original_locator}' should have been '{expected}' but it was '{value}'."
        )
        if ignore_case:
            expected = expected.lower()
            value = value.lower()
        if expected != value:
            raise AssertionError(msg)

    @keyword(tags=("IMPLEMENTED",))
    def element_text_should_not_be(
        self,
        locator: WebElement,
        not_expected: Optional[str],
        message: Optional[str] = None,
        ignore_case: bool = False,
    ):
        msg = (
            message
            or f"The text of element '{locator.original_locator}' was not supposed to be '{not_expected}'."
        )
        value = self.b.get_text(locator)
        if ignore_case:
            not_expected = not_expected.lower()
            value = value.lower()
        if not_expected == value:
            raise AssertionError(msg)

    @keyword
    def execute_async_javascript(self, *code: str):
        ...

    @keyword(tags=("IMPLEMENTED", "HAS LIMITATIONS"))
    def execute_javascript(self, *code: Any):
        """`Execute Javascript` has the limitation, that only the first argument (``argument[0]``) can be a webelement."""
        javascript, args = self._analyse_js(code)
        logger.debug(javascript)
        web_elem = None
        if args and isinstance(args[0], WebElement):
            elem = args.pop(0)
            return self.b.evaluate_javascript(
                elem,
                "(elem, args) => {\nlet arguments = [elem, ...args];\n" f"{javascript}" "}",
                arg=args,
            )
        return self.b.evaluate_javascript(
            None, f"(arguments) => {{{javascript}}}", arg=args or None
        )

    def _analyse_js(self, code):
        js = []
        args = []
        if "JAVASCRIPT" in code or "ARGUMENTS" in code:
            scope = js
            for line in code:
                if line == "JAVASCRIPT":
                    scope = js
                elif line == "ARGUMENTS":
                    scope = args
                else:
                    scope.append(line)
            javascript = "".join(js)
        else:
            javascript = "".join(code)
        if Path(javascript).is_file():
            javascript = Path(javascript).read_text(encoding="utf-8")
        return javascript, args

    @keyword(tags=("IMPLEMENTED",))
    def frame_should_contain(self, locator: WebElement, text: str, loglevel: str = "TRACE"):
        self.log_source(loglevel)
        self.b.get_element_count(f"{locator} >>> text={text}", GREATER_THAN, 0)

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
    def get_cookie(self, name: str) -> CookieInformation:
        try:
            raw_cookie = self.b.get_cookie(name, CookieType.dict)
        except ValueError as e:
            raise CookieNotFound(f"Cookie with name '{name}' not found.") from e
        cookie = CookieInformation(**raw_cookie)
        return cookie

    @keyword(tags=("IMPLEMENTED",))
    def get_cookies(self, as_dict: bool = False):
        if as_dict:
            cookies = {cookie.name: cookie.value for cookie in self.b.get_cookies()}
            return DotDict(cookies)
        else:
            pairs = []
            for cookie in self.b.get_cookies():
                pairs.append(f"{cookie['name']}={cookie['value']}")
            return "; ".join(pairs)

    @keyword(tags=("IMPLEMENTED",))
    def get_element_attribute(self, locator: WebElement, attribute: str):
        try:
            self.b.get_element_states(locator, CONTAINS, "attached")
        except AssertionError:
            raise ElementNotFound(f"Element with locator '{locator.original_locator}' not found.")
        try:
            return self.b.get_property(locator, attribute)
        except AttributeError:
            try:
                return self.b.get_attribute(locator, attribute)
            except AttributeError:
                return None

    @keyword(tags=("IMPLEMENTED",))
    def get_element_count(self, locator: WebElement):
        return self.b.get_element_count(locator)

    @keyword(tags=("IMPLEMENTED",))
    def get_element_size(self, locator: WebElement):
        try:
            self.b.get_element_states(locator, CONTAINS, "attached")
        except AssertionError:
            raise ElementNotFound(f"Element with locator '{locator.original_locator}' not found.")
        value = self.b.get_boundingbox(locator, BoundingBoxFields.ALL)
        return value["width"], value["height"]

    @keyword(tags=("IMPLEMENTED",))
    def get_horizontal_position(self, locator: WebElement):
        try:
            self.b.get_element_states(locator, CONTAINS, "attached")
        except AssertionError:
            raise ElementNotFound(f"Element with locator '{locator.original_locator}' not found.")
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
        current_page = self._get_current_page_id()
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
            return self._get_current_page_ids()
        if browser.upper() == "ALL":
            return list(self._get_all_page_ids())

        id = self._get_pw_browser_id(browser)
        org_browser = self.b.switch_browser(id)
        try:
            return self._get_current_page_ids()
        finally:
            self.b.switch_browser(org_browser)

    def _get_current_page_ids(self) -> List[str]:
        pw_page_ids = self.b.get_page_ids(browser=SelectionType.CURRENT)
        current_browser_id = self._get_current_browser_id()
        for pw_page_id in pw_page_ids:
            if pw_page_id not in self._browser_page_catalog[current_browser_id]:
                self._browser_page_catalog[current_browser_id].append(pw_page_id)
        for page_id in self._browser_page_catalog[current_browser_id]:
            if page_id not in pw_page_ids:
                self._browser_page_catalog[current_browser_id].remove(page_id)
        return self._browser_page_catalog[current_browser_id]

    def _get_all_page_ids(self) -> Generator[str, None, None]:
        catalog = self.b.get_browser_catalog()
        page_ids = []
        for browser in catalog:
            for context in browser["contexts"]:
                for page in context["pages"]:
                    page_ids.append(page["id"])
                    if page["id"] not in self._browser_page_catalog[browser["id"]]:
                        self._browser_page_catalog[browser["id"]].append(page["id"])
            for page_id in self._browser_page_catalog[browser["id"]]:
                if page_id not in page_ids:
                    self._browser_page_catalog[browser["id"]].remove(page_id)
        for browser in self._browser_page_catalog:
            for page in self._browser_page_catalog[browser]:
                yield page

    def _get_pw_browser_id(self, browser):
        if isinstance(browser, str) and browser.upper() == "CURRENT":
            return self._get_current_browser_id()
        id = self._browser_indexes.get(browser, None) or self._browser_indexes.get(
            self._browser_aliases.get(browser), None
        )
        if id is None:
            raise ValueError(f"Browser '{browser}' not found")
        return id

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
        ...

    @keyword(tags=("IMPLEMENTED",))
    def get_selenium_timeout(self):
        return self.b.timeout

    @keyword
    def get_session_id(self):
        ...

    @keyword(tags=("IMPLEMENTED",))
    def get_source(self):
        self.b.get_page_source()

    @keyword(tags=("IMPLEMENTED",))
    def get_table_cell(
        self,
        locator: WebElement,
        row: int,
        column: int,
        loglevel: str = "TRACE",
    ):
        if row == 0 or column == 0:
            raise ValueError(
                "Both row and column must be non-zero, " f"got row {row} and column {column}."
            )
        try:
            return self._get_cell_text(locator=locator, row=row, column=column)
        except Exception as e:
            self.log_source(loglevel)
            raise e

    def _get_cell_text(self, locator: WebElement, row, column):
        rows = self._get_rows(locator, row)
        if len(rows) < abs(row):
            raise AssertionError(
                f"Table '{locator.original_locator}' should have had at least {abs(row)} "
                f"rows but had only {len(rows)}."
            )
        index = row - 1 if row > 0 else row
        if column < 0:
            column_cnt = self.b.get_element_count(f"{rows[index]} >> xpath=./th|./td") + column
            if column_cnt < 0:
                raise AssertionError(
                    f"Table '{locator.original_locator}' should have had at least {abs(column)} "
                    f"columns but had only {column_cnt}."
                )
        else:
            column_cnt = column - 1
        cell_cnt = self.b.get_element_count(f"{rows[index]} >> xpath=./th|./td")
        if cell_cnt < abs(column):
            raise AssertionError(
                f"Table '{locator.original_locator}' row {row} should have had at "
                f"least {abs(column)} columns but had only {cell_cnt}."
            )
        txt = self.b.get_text(f"{rows[index]} >> xpath=./th|./td >> nth={column_cnt}")
        return txt

    def _get_rows(self, locator, count):
        cnt = self.b.get_element_count(f"{locator} >> thead > tr")
        rows = [f"{locator} >> thead > tr >> nth={index}" for index in range(cnt)]
        if count < 0 or len(rows) < count:
            cnt = self.b.get_element_count(f"{locator} >> tbody > tr")
            rows.extend([f"{locator} >> tbody > tr >> nth={index}" for index in range(cnt)])
        if count < 0 or len(rows) < count:
            cnt = self.b.get_element_count(f"{locator} >> tfoot > tr")
            rows.extend([f"{locator} >> tfoot > tr >> nth={index}" for index in range(cnt)])
        return rows

    @keyword(tags=("IMPLEMENTED",))
    def get_text(self, locator: WebElement):
        try:
            return self.b.get_text(locator)
        except Exception as e:
            raise ElementNotFound(
                f"Element with locator '{locator.original_locator}' not found."
            ) from e

    @keyword(tags=("IMPLEMENTED",))
    def get_title(self):
        return self.b.get_title()

    @keyword(tags=("IMPLEMENTED",))
    def get_value(self, locator: WebElement):
        return self.b.get_text(locator)

    @keyword(tags=("IMPLEMENTED",))
    def get_vertical_position(self, locator: WebElement):
        try:
            self.b.get_element_states(locator, CONTAINS, "attached")
        except AssertionError:
            raise ElementNotFound(f"Element with locator '{locator.original_locator}' not found.")
        return self.b.get_boundingbox(locator, BoundingBoxFields.y)

    @keyword(tags=("IMPLEMENTED",))
    def get_webelement(self, locator: WebElement):
        try:
            loc = WebElement(self.b.get_element(locator))
            loc.original_locator = locator.original_locator
            return loc
        except Exception as e:
            raise ElementNotFound(
                f"Element with locator '{locator.original_locator}' not found."
            ) from e

    @keyword(tags=("IMPLEMENTED",))
    def get_webelements(self, locator: WebElement):
        return self.b.get_elements(locator)

    @keyword(tags=("IMPLEMENTED",))
    def get_window_handles(self, browser: str = "CURRENT"):
        return self._get_page_ids(browser)

    @keyword(tags=("IMPLEMENTED",))
    def get_window_identifiers(self, browser: str = "CURRENT"):
        current_page = self._get_current_page_id()
        try:
            return list(self._generate_window_ids(browser))
        finally:
            self.b.switch_page(current_page, context=SelectionType.ALL, browser=SelectionType.ALL)

    def _generate_window_ids(self, browser: str):
        for page_id in self._get_page_ids(browser):
            self.b.switch_page(page_id, context=SelectionType.ALL, browser=SelectionType.ALL)
            yield self.b.evaluate_javascript(None, "() => String(window.id)") or "undefined"

    @keyword(tags=("IMPLEMENTED",))
    def get_window_names(self, browser: str = "CURRENT"):
        current_page = self._get_current_page_id()
        try:
            return list(self._generate_window_names(browser))
        finally:
            self.b.switch_page(current_page, context=SelectionType.ALL, browser=SelectionType.ALL)

    def _generate_window_names(self, browser: str):
        for page_id in self._get_page_ids(browser):
            self.b.switch_page(page_id, context=SelectionType.ALL, browser=SelectionType.ALL)
            yield self.b.evaluate_javascript(None, "() => String(window.name)") or "undefined"

    @keyword(tags=("IMPLEMENTED",))
    def get_window_position(self):
        return tuple(self.b.evaluate_javascript(None, "() => [window.screenX, window.screenY]"))

    @keyword(tags=("IMPLEMENTED",))
    def get_window_size(self, inner: bool = False):
        scope = "inner" if inner else "outer"
        return self.b.evaluate_javascript(
            None, f"() => [window.{scope}Width, window.{scope}Height]"
        )

    @keyword(tags=("IMPLEMENTED",))
    def get_window_titles(self, browser: str = "CURRENT"):
        current_page = self._get_current_page_id()
        try:
            return list(self._generate_titles(browser))
        finally:
            self.b.switch_page(current_page, context=SelectionType.ALL, browser=SelectionType.ALL)

    def _generate_titles(self, browser: str):
        for page_id in self._get_page_ids(browser):
            self.b.switch_page(page_id, context=SelectionType.ALL, browser=SelectionType.ALL)
            yield self.b.get_title()

    def _get_current_page_id(self):
        return self.b.get_page_ids(
            page=SelectionType.CURRENT, context=SelectionType.CURRENT, browser=SelectionType.CURRENT
        )[0]

    def _get_current_browser_id(self):
        return self.b.get_browser_ids(browser=SelectionType.CURRENT)[0]

    @keyword(tags=("IMPLEMENTED",))
    def go_back(self):
        self.b.go_back()

    @keyword(tags=("IMPLEMENTED",))
    def go_to(self, url):
        self.b.go_to(url)

    @keyword
    def handle_alert(self, action: str = "ACCEPT", timeout: Optional[timedelta] = None):
        ...

    @keyword(tags=("IMPLEMENTED",))
    def input_password(self, locator: WebElement, password: str, clear: bool = True):
        org_level = BuiltIn().set_log_level(level="NONE")
        try:
            self.b.press_keys(locator, "End")
            self.input_text(locator, password, clear)
        finally:
            BuiltIn().set_log_level(level=org_level)

    @keyword(tags=("IMPLEMENTED",))
    def input_text(self, locator: WebElement, text: str, clear: bool = True):
        if self.b.get_property(locator, "nodeName") == "INPUT":
            if self.b.get_attribute(locator, "type").lower() == "file":
                self.choose_file(locator, text)
                return
        self.b.press_keys(locator, "End")
        try:
            self.b.type_text(locator, text, clear=clear)
        except Exception as e:
            if not clear:
                raise e
            self.b.fill_text(locator, text)

    @keyword
    def input_text_into_alert(
        self, text: str, action: str = "ACCEPT", timeout: Optional[timedelta] = None
    ):
        ...

    @keyword(tags=("IMPLEMENTED",))
    def list_selection_should_be(self, locator: WebElement, *expected: str):
        try:
            self.b.get_element_states(locator, CONTAINS, "attached")
        except AssertionError:
            raise ElementNotFound("Page should have contained list 'nonexisting' but did not.")
        selected_labels = self.b.get_selected_options(locator, SelectAttribute.label)
        selected_values = self.b.get_selected_options(locator, SelectAttribute.value)
        expected_str = " | ".join(expected)
        actual_str = " | ".join(
            [f"{label} ({value})" for label, value in zip(selected_labels, selected_values)]
        )
        assert sorted(selected_labels) == sorted(expected) or sorted(selected_values) == sorted(
            expected
        ), f"List '{locator.original_locator}' should have had selection [ {expected_str} ] but selection was [ {actual_str} ]."

    @keyword(tags=("IMPLEMENTED",))
    def list_should_have_no_selections(self, locator: WebElement):
        # self.b.get_selected_options(locator, SelectAttribute.label, EQUALS)
        selected_labels = self.b.get_selected_options(locator, SelectAttribute.label)
        selected_values = self.b.get_selected_options(locator, SelectAttribute.value)
        actual_str = " | ".join(
            [f"{label} ({value})" for label, value in zip(selected_labels, selected_values)]
        )
        assert (
            len(selected_labels) == 0
        ), f"List '{locator.original_locator}' should have had no selection but selection was [ {actual_str} ]."

    @keyword(tags=("IMPLEMENTED",))
    def location_should_be(self, url: str, message: Optional[str] = None):
        self.b.get_url(
            EQUALS, url, message or "Location should have been {expected} but was {value}."
        )

    @keyword(tags=("IMPLEMENTED",))
    def location_should_contain(self, expected: str, message: Optional[str] = None):
        self.b.get_url(
            CONTAINS,
            expected,
            message or "Location should have contained {expected} but it was {value}.",
        )

    @keyword(tags=("IMPLEMENTED",))
    def log_location(self):
        location = self.b.get_url()
        logger.info(location)
        return location

    @keyword(tags=("IMPLEMENTED",))
    def log_source(self, loglevel: str = "INFO"):
        if loglevel.upper() == "NONE":
            return None
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
        try:
            self.b.get_element_states(locator, CONTAINS, "attached")
        except AssertionError:
            raise ElementNotFound(f"Element with locator '{locator.original_locator}' not found.")
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
        try:
            self.b.get_element_states(locator, CONTAINS, "attached")
        except AssertionError:
            raise ElementNotFound(f"Element with locator '{locator.original_locator}' not found.")
        bbox = self.b.get_boundingbox(locator, BoundingBoxFields.ALL)
        self.b.hover(locator)
        self.b.mouse_move_relative_to(locator, bbox.width / 2 + 1, bbox.height / 2 + 1, steps=10)

    @keyword(tags=("IMPLEMENTED",))
    def mouse_over(self, locator: WebElement):
        try:
            self.b.get_element_states(locator, CONTAINS, "attached")
        except AssertionError:
            raise ElementNotFound(f"Element with locator '{locator.original_locator}' not found.")
        self.b.hover(locator)

    @keyword(tags=("IMPLEMENTED",))
    def mouse_up(self, locator: WebElement):
        try:
            self.b.get_element_states(locator, CONTAINS, "attached")
        except AssertionError:
            raise ElementNotFound(f"Element with locator '{locator.original_locator}' not found.")
        self.b.hover(locator)
        self.b.mouse_button(MouseButtonAction.up)

    @keyword(tags=("IMPLEMENTED",))
    def open_browser(
        self,
        url: Optional[str] = None,
        browser: str = "chrome",
        alias: Optional[str] = None,
        remote_url: Union[bool, str] = False,
        desired_capabilities: Union[dict, None, str] = None,
        ff_profile_dir: Optional[str] = None,
        options: Any = None,
        service_log_path: Optional[str] = None,
        executable_path: Optional[str] = None,
    ):
        browser_enum, headless = BROWSERS.get(browser, (SupportedBrowsers.chromium, False))
        browser_id, context_id, page_info = self.b.new_persistent_context(
            url=url, browser=browser_enum, args=options, headless=headless, viewport=None
        )
        identifier = str(next(self._browser_index))
        self._browser_indexes[identifier] = browser_id
        self._browser_page_catalog[browser_id] = [page_info["page_id"]]
        if alias:
            self._browser_aliases[alias] = identifier
        return identifier

    @keyword(tags=("IMPLEMENTED",))
    def open_context_menu(self, locator: WebElement):
        self.b.click(locator, MouseButton.right)

    @keyword(tags=("IMPLEMENTED",))
    def page_should_contain(self, text: str, loglevel: str = "TRACE"):
        assert self.page_contains(
            f"text={text}"
        ), f"Page should have contained text '{text}' but did not."

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
        raise AssertionError(
            message
            or f"Page should have contained button '{locator.original_locator}' but did not."
        )

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
        raise AssertionError(
            message
            or f"Page should have contained checkbox '{locator.original_locator}' but did not."
        )

    @keyword(tags=("IMPLEMENTED",))
    def page_should_contain_element(
        self,
        locator: WebElement,
        message: Optional[str] = None,
        loglevel: str = "TRACE",
        limit: Optional[int] = None,
    ):
        try:
            count = self.b.get_element_count(locator)
        except Exception as e:
            logger.trace(e)
            count = 0
        if limit is not None:
            if count == limit:
                return
            self.log_source(loglevel)
            raise AssertionError(
                message
                or f'Page should have contained "{limit}" element(s), '
                f'but it did contain "{count}" element(s).'
            )
        if not count:
            self.log_source(loglevel)
            raise AssertionError(
                message
                or f"Page should have contained element '{locator.original_locator}' but did not."
            )

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
        raise AssertionError(
            message or f"Page should have contained image '{locator.original_locator}' but did not."
        )

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
        raise AssertionError(
            message or f"Page should have contained link '{locator.original_locator}' but did not."
        )

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
        raise AssertionError(
            message or f"Page should have contained list '{locator.original_locator}' but did not."
        )

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
        raise AssertionError(
            message
            or f"Page should have contained radio button '{locator.original_locator}' but did not."
        )

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
        raise AssertionError(
            message
            or f"Page should have contained text field '{locator.original_locator}' but did not."
        )

    @keyword(tags=("IMPLEMENTED",))
    def page_should_not_contain(self, text: str, loglevel: str = "TRACE"):
        try:
            assert not self.page_contains(
                f"text={text}"
            ), f"Page should not have contained text '{text}'."
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
            node = self.b.get_property(element, "nodeName")
            if node == "INPUT":
                self.log_source(loglevel)
                raise AssertionError(
                    message or f"Page should not have contained input '{locator.original_locator}'."
                )
            elif node == "BUTTON":
                self.log_source(loglevel)
                raise AssertionError(
                    message
                    or f"Page should not have contained button '{locator.original_locator}'."
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
                    message
                    or f"Page should not have contained checkbox '{locator.original_locator}'."
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
            raise AssertionError(
                message or f"Page should not have contained element '{locator.original_locator}'."
            )

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
                raise AssertionError(
                    message or f"Page should not have contained image '{locator.original_locator}'."
                )

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
                raise AssertionError(
                    message or f"Page should not have contained link '{locator.original_locator}'."
                )

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
                raise AssertionError(
                    message or f"Page should not have contained list '{locator.original_locator}'."
                )

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
                    message
                    or f"Page should not have contained radio button '{locator.original_locator}'."
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
                    message
                    or f"Page should not have contained text field '{locator.original_locator}'."
                )

    @keyword(tags=("IMPLEMENTED",))
    def press_key(self, locator: WebElement, key: str):
        if key.startswith("\\") and len(key) > 1:
            key = self._map_ascii_key_code_to_key(int(key[1:]))
        try:
            self.b.get_element_states(locator, CONTAINS, "attached")
        except AssertionError:
            raise ElementNotFound(f"Element with locator '{locator.original_locator}' not found.")
        if isinstance(key, Keys):
            self.b.keyboard_key(KeyAction.press, key.value)
        else:
            self.press_keys(locator, key)

    def _map_ascii_key_code_to_key(self, key_code):
        map = {
            0: Keys.NULL,
            8: Keys.BACK_SPACE,
            9: Keys.TAB,
            10: Keys.RETURN,
            13: Keys.ENTER,
            24: Keys.CANCEL,
            27: Keys.ESCAPE,
            32: Keys.SPACE,
            42: Keys.MULTIPLY,
            43: Keys.ADD,
            44: Keys.SEPARATOR,
            45: Keys.SUBTRACT,
            56: Keys.DECIMAL,
            57: Keys.DIVIDE,
            59: Keys.SEMICOLON,
            61: Keys.EQUALS,
            127: Keys.DELETE,
        }
        key = map.get(key_code)
        if key is None:
            key = chr(key_code)
        return key

    @keyword(tags=("IMPLEMENTED",))
    def press_keys(self, locator: Optional[WebElement] = None, *keys: str):
        parsed_keys = self._parse_keys(*keys)
        if not self._is_noney(locator):
            logger.info(f"Sending key(s) {keys} to {locator.original_locator} element.")
            try:
                self.b.get_element_states(locator, CONTAINS, "attached")
            except AssertionError:
                raise ElementNotFound(
                    f"Element with locator '{locator.original_locator}' not found."
                )
            self.b.click(
                locator
            )  # ToDo: i would consider this a bug. it should focus; not click...
        else:
            logger.info(f"Sending key(s) {keys} to page.")
        for parsed_key in parsed_keys:
            for key in parsed_key:
                if key.special:
                    self.b.keyboard_key(KeyAction.down, key.converted.value)
                else:
                    for char in key.converted:
                        try:
                            self.b.keyboard_key(KeyAction.press, char)
                        except Exception:
                            self.b.keyboard_input(KeyboardInputAction.type, char)
            self._special_key_up(None, parsed_key)

    def _special_key_up(self, actions, parsed_key):
        for key in reversed(parsed_key):
            if key.special:
                self.b.keyboard_key(KeyAction.up, key.converted.value)

    def _is_noney(self, item):
        return (
            item is None or isinstance(item, WebElement) and item.original_locator.upper() == "NONE"
        )

    def _parse_keys(self, *keys):
        if not keys:
            raise AssertionError('"keys" argument can not be empty.')
        list_keys = []
        for key in keys:
            separate_keys = self._separate_key(key)
            separate_keys = self._convert_special_keys(separate_keys)
            list_keys.append(separate_keys)
        return list_keys

    def _separate_key(self, key):
        one_key = ""
        list_keys = []
        for char in key:
            if char == "+" and one_key != "":
                list_keys.append(one_key)
                one_key = ""
            else:
                one_key += char
        if one_key:
            list_keys.append(one_key)
        return list_keys

    def _convert_special_keys(self, keys):
        KeysRecord = namedtuple("KeysRecord", "converted, original special")
        converted_keys = []
        for key in keys:
            key = self._parse_aliases(key)
            if self._selenium_keys_has_attr(key):
                converted_keys.append(KeysRecord(getattr(Keys, key), key, True))
            else:
                converted_keys.append(KeysRecord(key, key, False))
        return converted_keys

    def _parse_aliases(self, key):
        if key == "CTRL":
            return "CONTROL"
        if key == "ESC":
            return "ESCAPE"
        return key

    def _selenium_keys_has_attr(self, key):
        return hasattr(Keys, key)

    @keyword(tags=("IMPLEMENTED",))
    def radio_button_should_be_set_to(self, group_name: str, value: str):
        selector = f"css=input[type='radio'][name='{group_name}']"
        try:
            self.b.get_element_count(selector, GREATER_THAN, 0)
        except AssertionError:
            raise ElementNotFound(f"No radio button with name '{group_name}' found.")
        radios = self.b.get_elements(selector)
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
        ...

    @keyword(tags=("IMPLEMENTED",))
    def reload_page(self):
        self.b.reload()

    @keyword
    def remove_location_strategy(self, strategy_name: str):
        ...

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
            raise ElementNotFound(f"Checkbox with locator '{locator.original_locator}' not found.")
        self.b.check_checkbox(locator)

    @keyword(tags=("IMPLEMENTED",))
    def select_frame(self, locator: WebElement):
        try:
            self.b.get_property(locator, "nodeName", AO.validate, "value in ['IFRAME', 'FRAME']")
        except AssertionError:
            raise NoSuchFrameException(
                f"Message: Unable to locate frame for element: {self.b.get_url()}"
            )
        self.b.set_selector_prefix(f"{locator} >>>", scope=Scope.Global)

    @keyword(tags=("IMPLEMENTED",))
    def select_from_list_by_index(self, locator: WebElement, *indexes: str):
        if self.b.get_property(locator, "multiple"):
            selection = self.b.get_selected_options(locator, SelectAttribute.index)
            indexes = [*indexes, *selection]
        self.b.select_options_by(locator, SelectAttribute.index, *indexes)

    @keyword(tags=("IMPLEMENTED",))
    def select_from_list_by_label(self, locator: WebElement, *labels: str):
        existing_labels = [option["label"] for option in self.b.get_select_options(locator)]
        for label in labels:
            if label not in existing_labels:
                raise NoSuchElementException(
                    f"Message: Could not locate element with visible text: {label}"
                )
        if self.b.get_property(locator, "multiple"):
            selection = self.b.get_selected_options(locator, SelectAttribute.label)
            labels = [*labels, *selection]
        self.b.select_options_by(locator, SelectAttribute.label, *labels)

    @keyword(tags=("IMPLEMENTED",))
    def select_from_list_by_value(self, locator: WebElement, *values: str):
        existing_values = [option["value"] for option in self.b.get_select_options(locator)]
        for value in values:
            if value not in existing_values:
                raise NoSuchElementException(f"Message: Cannot locate option with value: {value}")
        if self.b.get_property(locator, "multiple"):
            selection = self.b.get_selected_options(locator, SelectAttribute.value)
            values = [*values, *selection]
        self.b.select_options_by(locator, SelectAttribute.value, *values)

    @keyword(tags=("IMPLEMENTED",))
    def select_radio_button(self, group_name: str, value: str):
        selector = WebElement(
            f"input[type='radio'][name='{group_name}'][value='{value}'],"
            f"input[type='radio'][name='{group_name}']#{value}"
        )
        try:
            self.b.get_element_count(selector, GREATER_THAN, 0)
        except AssertionError:
            raise AssertionError(
                f"No radio button with name '{group_name}' and value '{value}' found."
            )
        self.b.check_checkbox(selector)

    @keyword
    def set_browser_implicit_wait(self, value: timedelta):
        ...

    @keyword(tags=("IMPLEMENTED",))
    def set_focus_to_element(self, locator: WebElement):
        self.b.focus(locator)

    @keyword(tags=("IMPLEMENTED",))
    def set_screenshot_directory(self, path: Optional[str]):
        previous = self.screenshot_root_directory
        self.screenshot_root_directory = path
        return previous

    @keyword
    def set_selenium_implicit_wait(self, value: timedelta):
        return self.b.set_browser_timeout(value)

    @keyword
    def set_selenium_page_load_timeout(self, value: timedelta) -> str:
        ...

    @keyword(tags=("IMPLEMENTED",))
    def set_selenium_speed(self, value: timedelta):
        return self.b.millisecs_to_timestr(self.b.convert_timeout(value))

    @keyword(tags=("IMPLEMENTED",))
    def set_selenium_timeout(self, value: timedelta):
        return self.b.set_browser_timeout(value)

    @keyword
    def set_window_position(self, x: int, y: int):
        ...

    @keyword(tags=("IMPLEMENTED", "HAS LIMITATIONS"))
    def set_window_size(self, width: int, height: int, inner: bool = False):
        """It does not actually set the size of the browser window, but the size of the viewport."""
        self.b.set_viewport_size(width, height)

    @keyword(tags=("IMPLEMENTED",))
    def simulate_event(self, locator: WebElement, event: str):
        try:
            self.b.get_element_states(locator, CONTAINS, "attached")
        except AssertionError:
            raise ElementNotFound(f"Element with locator '{locator.original_locator}' not found.")
        script = """(element, eventName) => {
                var evt = document.createEvent("HTMLEvents");
                evt.initEvent(eventName, true, true);
                return !element.dispatchEvent(evt);
            }
        """
        self.b.evaluate_javascript(locator, script, arg=event)

    @keyword(tags=("IMPLEMENTED",))
    def submit_form(self, locator: Optional[WebElement] = None):
        if locator is None:
            locator = WebElement("css=form >> nth=0")
        node = self.b.get_property(locator, "nodeName")
        if node != "FORM":
            raise ElementNotFound(f"Form with locator '{locator.original_locator}' not found.")
        self.b.evaluate_javascript(locator, "form => form.submit()")

    @keyword(tags=("IMPLEMENTED",))
    def switch_browser(self, index_or_alias: Union[int, str]):
        id = self._browser_indexes.get(index_or_alias, None) or self._browser_indexes.get(
            self._browser_aliases.get(index_or_alias), None
        )
        if id is None:
            raise ValueError(f"Browser '{index_or_alias}' not found")
        return self.b.switch_browser(id)

    @keyword(tags=("IMPLEMENTED",))
    def switch_window(
        self,
        locator: Union[list, str] = "MAIN",
        timeout: Optional[str] = None,
        browser: str = "CURRENT",
    ):
        log_level = BuiltIn().set_log_level("ERROR")
        try:
            epoch = time.time()
            timeout = epoch if not timeout else timestr_to_secs(timeout) + epoch
            current_page_id = self._get_current_page_id()
            while True:
                try:
                    if isinstance(locator, str):
                        if locator.upper() == "CURRENT":
                            return current_page_id
                        if locator.upper() == "NEW":
                            id = self._get_pw_browser_id(browser)
                            if id != self._get_current_browser_id:
                                self.b.switch_browser(id)
                            self.b.switch_page("NEW")
                            return current_page_id
                        locator_match = re.match(
                            r"(?P<strategy>name|title|url|default)[:=](?P<locator>.*)", locator
                        )
                        if locator_match:
                            locator = locator_match.group("locator")
                            strategy = locator_match.group("strategy")
                        else:
                            strategy = "default"
                        for index, page_info in enumerate(
                            self._generate_window_information(browser)
                        ):
                            if strategy == "default" and page_info["handle"] == locator:
                                return current_page_id
                            if strategy in ["default", "name"] and page_info["name"] == locator:
                                return current_page_id
                            if strategy in ["default", "title"] and page_info["title"] == locator:
                                return current_page_id
                            if strategy in ["default", "url"] and page_info["url"] == locator:
                                return current_page_id
                            if strategy == "default" and locator.upper() == "MAIN" and index == 0:
                                return current_page_id
                        self.b.switch_page(current_page_id)
                    else:
                        for page_id in self._get_page_ids(browser):
                            if page_id not in locator:
                                self.b.switch_page(page_id, SelectionType.ALL, SelectionType.ALL)
                                return current_page_id
                    raise WindowNotFound(
                        f"No window matching handle, name, title or URL '{locator}' found."
                    )
                except WindowNotFound as e:
                    if time.time() > timeout:
                        raise e
                    time.sleep(0.1)
        finally:
            BuiltIn().set_log_level(log_level)

    def _generate_window_information(self, browser: str):
        for page_id in self._get_page_ids(browser):
            self.b.switch_page(page_id, context=SelectionType.ALL, browser=SelectionType.ALL)
            name = self.b.evaluate_javascript(None, "() => String(window.name)")
            title = self.b.get_title()
            url = self.b.get_url()
            handle = page_id
            yield {"handle": handle, "name": name, "title": title, "url": url}

    def _index_to_position(self, index):
        if index == 0:
            raise ValueError("Row and column indexes must be non-zero.")
        if index > 0:
            return str(index)
        if index == -1:
            return "position()=last()"
        return f"position()=last()-{abs(index) - 1}"

    @keyword(tags=("IMPLEMENTED",))
    def table_cell_should_contain(
        self,
        locator: WebElement,
        row: int,
        column: int,
        expected: str,
        loglevel: str = "TRACE",
    ):
        tc_text = self.get_table_cell(locator=locator, row=row, column=column, loglevel=loglevel)
        if expected not in tc_text:
            self.log_source(loglevel)
            raise AssertionError(
                f"Table '{locator.original_locator}' cell on row {row} and column {column} "
                f"should have contained text '{expected}' but it had '{tc_text}'."
            )
        logger.info(f"Table cell contains '{tc_text}'.")

    @keyword(tags=("IMPLEMENTED",))
    def table_column_should_contain(
        self,
        locator: WebElement,
        column: int,
        expected: str,
        loglevel: str = "TRACE",
    ):
        position = self._index_to_position(column)
        if (
            self.b.get_element_count(
                f"{locator} >> //tr//*[self::td or self::th][{position}] >> text={expected}"
            )
            == 0
        ):
            self.log_source(loglevel)
            raise AssertionError(
                f"Table '{locator.original_locator}' column {column} did not contain text '{expected}'."
            )

    @keyword(tags=("IMPLEMENTED",))
    def table_footer_should_contain(
        self,
        locator: WebElement,
        expected: str,
        loglevel: str = "TRACE",
    ):
        if self.b.get_element_count(f"{locator} >> //tfoot//td >> text={expected}") == 0:
            self.log_source(loglevel)
            raise AssertionError(
                f"Table '{locator.original_locator}' footer did not contain text '{expected}'."
            )

    @keyword(tags=("IMPLEMENTED",))
    def table_header_should_contain(
        self,
        locator: WebElement,
        expected: str,
        loglevel: str = "TRACE",
    ):
        for i in range(self.b.get_element_count(f"{locator} >> //th")):
            if expected in self.b.get_text(f"{locator} >> //th >> nth={i}"):
                return
        self.log_source(loglevel)
        raise AssertionError(
            f"Table '{locator.original_locator}' header did not contain text '{expected}'."
        )

    @keyword(tags=("IMPLEMENTED",))
    def table_row_should_contain(
        self,
        locator: WebElement,
        row: int,
        expected: str,
        loglevel: str = "TRACE",
    ):
        position = self._index_to_position(row)
        for i in range(self.b.get_element_count(f"{locator} >> //tr[{position}]")):
            if expected in self.b.get_text(f"{locator} >> //tr[{position}] >> nth={i}").replace(
                "\t", " "
            ):
                return
        self.log_source(loglevel)
        raise AssertionError(
            f"Table '{locator.original_locator}' row {row} did not contain text '{expected}'."
        )

    @keyword(tags=("IMPLEMENTED",))
    def table_should_contain(
        self,
        locator: WebElement,
        expected: str,
        loglevel: str = "TRACE",
    ):
        if self.b.get_element_count(f"{locator} >> text={expected}") == 0:
            self.log_source(loglevel)
            raise AssertionError(
                f"Table '{locator.original_locator}' did not contain text '{expected}'."
            )

    @keyword(tags=("IMPLEMENTED",))
    def textarea_should_contain(
        self,
        locator: WebElement,
        expected: str,
        message: Optional[str] = None,
    ):
        for element in self.b.get_elements(locator):
            if self.b.get_property(element, "nodeName") == "TEXTAREA":
                try:
                    text = self.b.get_text(locator)
                except Exception as e:
                    raise ElementNotFound(
                        f"Textarea with locator '{locator.original_locator}' not found."
                    ) from e
                if expected not in text:
                    raise AssertionError(
                        message
                        or f"Text area '{locator.original_locator}' should have contained text '{expected}' but it had '{text}'."
                    )
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
                text = self.b.get_text(locator)
                if text != expected:
                    raise AssertionError(
                        message
                        or f"Text area '{locator.original_locator}' should have had text '{expected}' but it had '{text}'."
                    )
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
                text = self.b.get_text(locator)
                if expected not in text:
                    raise AssertionError(
                        message
                        or f"Text field '{locator.original_locator}' should have contained text '{expected}' but it contained '{text}'."
                    )
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
                text = self.b.get_text(locator)
                if text != expected:
                    raise AssertionError(
                        message
                        or f"Value of text field '{locator.original_locator}' should have been '{expected}' but was '{text}'."
                    )
                return
        raise AssertionError("Element is not a textfield")

    @keyword(tags=("IMPLEMENTED",))
    def title_should_be(self, title: str, message: Optional[str] = None):
        self.b.get_title(
            EQUALS, title, message or "Title should have been {expected} but was {value}."
        )

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
            raise ElementNotFound(f"Checkbox with locator '{locator.original_locator}' not found.")
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
        if not self.b.get_property(locator, "multiple"):
            raise RuntimeError("Un-selecting options works only with multi-selection lists.")
        if not labels:
            raise ValueError("No labels given.")
        existing_labels = [option["label"] for option in self.b.get_select_options(locator)]
        for label in labels:
            if label not in existing_labels:
                raise NoSuchElementException(
                    f"Message: Could not locate element with visible text: {label}"
                )
        selection = self.b.get_selected_options(locator, SelectAttribute.label)
        self.b.select_options_by(
            locator, SelectAttribute.label, *[s for s in selection if s not in labels]
        )

    @keyword(tags=("IMPLEMENTED",))
    def unselect_from_list_by_value(self, locator: WebElement, *values: str):
        if not self.b.get_property(locator, "multiple"):
            raise RuntimeError("Un-selecting options works only with multi-selection lists.")
        if not values:
            raise ValueError("No values given.")
        existing_values = [option["value"] for option in self.b.get_select_options(locator)]
        for value in values:
            if value not in existing_values:
                raise NoSuchElementException(
                    f"Message: Could not locate element with value: {value}"
                )
        selection = self.b.get_selected_options(locator, SelectAttribute.value)
        self.b.select_options_by(
            locator, SelectAttribute.value, *[s for s in selection if s not in values]
        )

    @keyword(tags=("IMPLEMENTED",))
    def wait_for_condition(
        self,
        condition: str,
        timeout: Optional[timedelta] = None,
        error: Optional[str] = None,
    ):
        if "return" not in condition:
            raise ValueError(f"Condition '{condition}' did not have mandatory 'return'.")
        self._wait_until(
            lambda: self.execute_javascript(condition) is True,
            f"Condition '{condition}' did not become true in <TIMEOUT>.",
            timeout,
            error,
        )

    @keyword(tags=("IMPLEMENTED",))
    def wait_until_element_contains(
        self,
        locator: WebElement,
        text: str,
        timeout: Optional[timedelta] = None,
        error: Optional[str] = None,
    ):
        self._wait_until(
            lambda: text in self.b.get_text(locator),
            f"Element '{locator.original_locator}' did not get text '{text}' in <TIMEOUT>.",
            timeout,
            error,
        )

    @keyword(tags=("IMPLEMENTED",))
    def wait_until_element_does_not_contain(
        self,
        locator: WebElement,
        text: str,
        timeout: Optional[timedelta] = None,
        error: Optional[str] = None,
    ):
        self._wait_until(
            lambda: text not in self.b.get_text(locator),
            f"Element '{locator.original_locator}' still had text '{text}' after <TIMEOUT>.",
            timeout,
            error,
        )

    @keyword(tags=("IMPLEMENTED",))
    def wait_until_element_is_enabled(
        self,
        locator: WebElement,
        timeout: Optional[timedelta] = None,
        error: Optional[str] = None,
    ):
        try:
            self.b.get_element_states(locator, CONTAINS, "attached")
        except AssertionError:
            raise ElementNotFound(f"Element with locator '{locator.original_locator}' not found.")
        self._wait_until(
            lambda: self.b.get_element_states(
                locator, THEN, "bool((value & (enabled | editable)) == (enabled | editable))"
            ),
            f"Element '{locator.original_locator}' was not enabled in <TIMEOUT>.",
            timeout,
            error,
        )

    @keyword(tags=("IMPLEMENTED",))
    def wait_until_element_is_not_visible(
        self,
        locator: WebElement,
        timeout: Optional[timedelta] = None,
        error: Optional[str] = None,
    ):
        self._wait_until(
            lambda: self.b.get_element_states(locator, THEN, "bool(value & (hidden | detached))"),
            f"Element '{locator.original_locator}' still visible after <TIMEOUT>.",
            timeout,
            error,
        )

    @keyword(tags=("IMPLEMENTED",))
    def wait_until_element_is_visible(
        self,
        locator: WebElement,
        timeout: Optional[timedelta] = None,
        error: Optional[str] = None,
    ):
        self._wait_until(
            lambda: self.b.get_element_states(locator, THEN, "bool(value & visible)"),
            f"Element '{locator.original_locator}' not visible after <TIMEOUT>.",
            timeout,
            error,
        )

    @keyword(tags=("IMPLEMENTED",))
    def wait_until_location_contains(
        self,
        expected: str,
        timeout: Optional[timedelta] = None,
        message: Optional[str] = None,
    ):
        self._wait_until(
            lambda: expected in self.b.get_url(),
            f"Location did not contain '{expected}' in <TIMEOUT>.",
            timeout,
            message,
        )

    @keyword(tags=("IMPLEMENTED",))
    def wait_until_location_does_not_contain(
        self,
        location: str,
        timeout: Optional[timedelta] = None,
        message: Optional[str] = None,
    ):
        self._wait_until(
            lambda: location not in self.b.get_url(),
            f"Location did contain '{location}' in <TIMEOUT>.",
            timeout,
            message,
        )

    @keyword(tags=("IMPLEMENTED",))
    def wait_until_location_is(
        self,
        expected: str,
        timeout: Optional[timedelta] = None,
        message: Optional[str] = None,
    ):
        self._wait_until(
            lambda: expected == self.b.get_url(),
            f"Location did not become '{expected}' in <TIMEOUT>.",
            timeout,
            message,
        )

    @keyword(tags=("IMPLEMENTED",))
    def wait_until_location_is_not(
        self,
        location: str,
        timeout: Optional[timedelta] = None,
        message: Optional[str] = None,
    ):
        self._wait_until(
            lambda: location != self.b.get_url(),
            f"Location is '{location}' in <TIMEOUT>.",
            timeout,
            message,
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
        locator: WebElement,
        timeout: Optional[timedelta] = None,
        error: Optional[str] = None,
        limit: Optional[int] = None,
    ):
        if limit is None:
            func = lambda: self.b.get_element_count(locator) > 0
            msg = f"Element '{locator.original_locator}' did not appear in <TIMEOUT>."
        else:
            func = lambda: self.b.get_element_count(locator) == limit
            msg = f'Page should have contained "{limit}" {locator.original_locator} element(s) within <TIMEOUT>.'
        self._wait_until(
            func,
            msg,
            timeout,
            error,
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
        locator: WebElement,
        timeout: Optional[timedelta] = None,
        error: Optional[str] = None,
        limit: Optional[int] = None,
    ):
        if limit is None:
            func = lambda: self.b.get_element_count(locator) == 0
            msg = f"Element '{locator.original_locator}' did not disappear in <TIMEOUT>."
        else:
            func = lambda: self.b.get_element_count(locator) != limit
            msg = f'Page should have not contained "{limit}" {locator.original_locator} element(s) within <TIMEOUT>.'
        self._wait_until(
            func,
            msg,
            timeout,
            error,
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

    def _create_directory(self, path):
        target_dir = Path(path).parent
        if not target_dir.exists():
            target_dir.mkdir(parents=True)

    def _get_screenshot_path(self, filename: str, embed: bool) -> str:
        if (
            embed
            or self.screenshot_root_directory
            and self.screenshot_root_directory.upper() == EMBED
        ):
            directory = self.log_dir
        else:
            directory = self.screenshot_root_directory or self.log_dir
        path = Path(directory, filename).resolve()
        self._create_directory(path)
        return str(path)

    def _decide_embedded(self, filename: str) -> bool:
        return (
            filename in [DEFAULT_FILENAME_PAGE, DEFAULT_FILENAME_ELEMENT]
            and self.screenshot_root_directory
            and self.screenshot_root_directory.upper() == EMBED
            or filename.upper() == EMBED
        )
