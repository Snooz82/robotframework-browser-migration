*** Test Cases ***
Importing SeleniumLibrary Should Fail If Plugin Is Not Found
    [Documentation]    When importing plugin from module, the SeleniumLibrary import fails and
    ...    therefore Open Browser keyword is not found.
    ...    FAIL REGEXP: (Initializing test library 'SeleniumLibrary'|Initializing library 'SeleniumLibrary' with arguments).*
    Import Library
    ...    SeleniumLibraryToBrowser
    ...    plugins=${CURDIR}/ModulePlugin.py

SeleniumLibrary Open Browser Keyword Should Not Be Found
    [Documentation]    FAIL No keyword with name 'Open Browser' found.
    Open Browser
    ...    foobar
    ...    Not Here
