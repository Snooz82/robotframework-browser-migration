*** Settings ***
Resource            resource.robot
Library             ../resources/testlibs/cache_error.py

Suite Teardown      Close All Browsers


*** Test Cases ***
Browser Should Open And Close
    Open Browser To Start Page Without Testing Default Options
    Close Browser

There Should Be A Good Error Message If Browser Is Not Opened
    Run Keyword And Expect Error    *    Title Should Be    foo

Close Browser Does Nothing When No Browser Is Opened
    Close Browser

Browser Open With Not Well-Formed URL Should Close
    [Documentation]    Verify after incomplete 'Open Browser' browser closes
    ...    LOG 1.1:20 DEBUG STARTS: Opened browser with session id
    ...    LOG 1.1:20 DEBUG REGEXP: .*but failed to open url.*
    ...    LOG 2:2 DEBUG STARTS: DELETE
    ...    LOG 2:5 DEBUG STARTS: Finished Request
    Run Keyword And Expect Error    *    Open Browser    bad.url.bad    ${BROWSER}
    Close All Browsers

Switch to closed browser is possible
    Open Browser    ${ROOT}/forms/prefilled_email_form.html    ${BROWSER}    Browser 1
    ...    remote_url=${REMOTE_URL}    desired_capabilities=${DESIRED_CAPABILITIES}
    Open Browser    ${ROOT}/forms/prefilled_email_form.html    ${BROWSER}    Browser 2
    ...    remote_url=${REMOTE_URL}    desired_capabilities=${DESIRED_CAPABILITIES}
    Open Browser    ${ROOT}/forms/prefilled_email_form.html    ${BROWSER}    Browser 3
    ...    remote_url=${REMOTE_URL}    desired_capabilities=${DESIRED_CAPABILITIES}
    Switch Browser    Browser 1
    Switch Browser    Browser 2
    Close Browser
    Switch Browser    Browser 3
    Page Should Contain    Name:
    Run Keyword And Expect Error
    ...    *
    ...    Switch Browser    Browser 2
    Close All Browsers

Closing all browsers clears cache
    Open Browser    ${ROOT}/forms/prefilled_email_form.html    ${BROWSER}    Browser 1
    ...    remote_url=${REMOTE_URL}    desired_capabilities=${DESIRED_CAPABILITIES}
    Open Browser    ${ROOT}/forms/prefilled_email_form.html    ${BROWSER}    Browser 2
    ...    remote_url=${REMOTE_URL}    desired_capabilities=${DESIRED_CAPABILITIES}
    Switch Browser    Browser 1
    Switch Browser    Browser 2
    Close All Browsers
    Run Keyword And Expect Error
    ...    *
    ...    Switch Browser    Browser 1
    Run Keyword And Expect Error
    ...    *
    ...    Switch Browser    Browser 2

Get Session Id
    Open Browser    ${ROOT}/forms/prefilled_email_form.html    ${BROWSER}    Browser 1
    ...    remote_url=${REMOTE_URL}    desired_capabilities=${DESIRED_CAPABILITIES}
    Open Browser    ${ROOT}/forms/prefilled_email_form.html    ${BROWSER}    Browser 2
    ...    remote_url=${REMOTE_URL}    desired_capabilities=${DESIRED_CAPABILITIES}
    Switch Browser    Browser 1
    ${browser 1}    Get Session Id
    Switch Browser    Browser 2
    ${browser 2}    Get Session Id
    Should Not Be Equal    ${browser 1}    ${browser 2}    Session id should be diffrent
    Close All Browsers
    Run Keyword And Expect Error
    ...    *
    ...    Switch Browser    Browser 1
    Run Keyword And Expect Error
    ...    *
    ...    Switch Browser    Browser 2

Open Browser desired_capabilities As Dictionary
    ${caps}    Create Dictionary    foo=${True}
    Open Browser    ${ROOT}/forms/prefilled_email_form.html    ${BROWSER}
    ...    remote_url=${REMOTE_URL}    desired_capabilities=${caps}

When Closing Browsers Causes An Error
    [Documentation]
    ...    FAIL    AttributeError: 'NoneType' object has no attribute 'quit'
    ...    LOG 3:10    ERROR When closing browser, received exception: 'NoneType' object has no attribute 'quit'
    ...    LOG 3:11    ERROR When closing browser, received exception: 'NoneType' object has no attribute 'quit'
    [Tags]    nogrid    robot:skip
    Open Browser    ${ROOT}/forms/prefilled_email_form.html    ${BROWSER}    Browser 1
    ...    remote_url=${REMOTE_URL}    desired_capabilities=${DESIRED_CAPABILITIES}
    Invalidate Driver
    Close All Browsers
