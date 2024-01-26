*** Settings ***
Documentation       Tests Scroll Into View Verification

Resource            ../resource.robot

Suite Setup         Open Browser To Start Page


*** Variables ***
${TEXT}=    You scrolled in div.


*** Test Cases ***
Verify Scroll Element Into View
    [Tags]    known issue firefox
    [Setup]    Go To Page "scroll/index.html"
    ${initial_postion}=    Get Vertical Position    css:#target
    Scroll Element Into View    css:#target
    Sleep    200ms
    ${postion}=    Get Vertical Position    css:#target
    Should Be True    ${initial_postion} > ${postion}
    Element Should Contain    css:#result    ${TEXT}
