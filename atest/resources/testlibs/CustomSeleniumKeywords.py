from robot.libraries.BuiltIn import BuiltIn
from SeleniumLibraryToBrowser import SeleniumLibraryToBrowser, keyword


class CustomSeleniumKeywords(SeleniumLibraryToBrowser):
    def __init__(self, *args, **kwargs):
        """Share `SeleniumLibrary`'s cache of browsers, so that
        we don't have to open a separate browser instance for the
        `Run On Failure Keyword Only Called Once` test."""
        super().__init__(*args, **kwargs)
        sl = BuiltIn().get_library_instance("SeleniumLibraryToBrowser")

    @keyword
    def custom_selenium_keyword(self):
        self.custom_selenium_keyword_inner()

    @keyword
    def custom_selenium_keyword_inner(self):
        raise AssertionError

    @keyword
    def use_find_element(self, locator, parent=None):
        return self.find_element(locator, parent)

    @keyword
    def use_find_elements(self, locator, parent=None):
        return self.find_elements(locator, parent)
