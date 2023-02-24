from robot.libraries.BuiltIn import BuiltIn


def my_choose_file(locator, path):
    sl = BuiltIn().get_library_instance("SeleniumLibraryToBrowser")
    sl.choose_file(locator, path)
