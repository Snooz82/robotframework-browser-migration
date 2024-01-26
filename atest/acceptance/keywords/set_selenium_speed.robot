*** Settings ***
Resource            ../resource.robot

Suite Setup         Go To Page "forms/prefilled_email_form.html"
Test Teardown       Set Selenium Speed    0


*** Test Cases ***
Settimg selenium speed is possible multiple times
    setseleniumspeed    1
    Set Selenium Speed    10
    ${old} =    Set Selenium Speed    1
    Should Be Equal    ${old}    10 seconds
    ${old} =    Set Selenium Speed    100
    Should Be Equal    ${old}    1 second

Selenium speed should affect execution
    [Documentation]    Click Element executes two selenium commands and
    ...    therefore total time is 2 seconds
    ...
    ...    But Browser only one therefore one... ;-) René
    Set Selenium Speed    1
    ${start} =    Get Time    epoch
    Click Element    xpath=//input[@name="email"]
    ${end} =    Get Time    epoch
    Should Be True    ${end} - ${start} >= ${1}

Selenium speed should affect before browser is opened
    [Documentation]    Click Element executes two selenium commands and
    ...    therefore total time is 2 seconds
    ...
    ...    But Browser only one therefore one... ;-) René
    Close All Browsers
    Set Selenium Speed    1
    Open Browser To "forms/prefilled_email_form.html"
    ${start} =    Get Time    epoch
    Click Element    xpath=//input[@name="email"]
    ${end} =    Get Time    epoch
    Should Be True    ${end} - ${start} >= ${1}

Selenium speed should affect all browsers
    [Documentation]    Click Element executes two selenium commands and
    ...    therefore total time is 2 seconds
    ...
    ...    But Browser only one therefore one... ;-) René
    Close All Browsers
    Open Browser To "forms/prefilled_email_form.html"
    Open Browser To "forms/prefilled_email_form.html"
    Set Selenium Speed    1
    ${start} =    Get Time    epoch
    Click Element    xpath=//input[@name="email"]
    ${end} =    Get Time    epoch
    Should Be True    ${end} - ${start} >= ${1}
    Switch Browser    ${2}
    ${start} =    Get Time    epoch
    Click Element    xpath=//input[@name="email"]
    ${end} =    Get Time    epoch
    Should Be True    ${end} - ${start} >= ${1}


*** Keywords ***
Open Browser To "forms/prefilled_email_form.html"
    ${index} =    Open Browser    ${FRONT PAGE}    ${BROWSER}
    ...    remote_url=${REMOTE_URL}    desired_capabilities=${DESIRED_CAPABILITIES}
    Go To    ${ROOT}/forms/prefilled_email_form.html
