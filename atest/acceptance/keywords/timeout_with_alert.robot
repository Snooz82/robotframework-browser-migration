*** Settings ***
Documentation       This tests the RF conversion than alters

Resource            ../resource.robot

Suite Setup         Set Global Timeout    1 second
Suite Teardown      Restore Global Timeout
Test Setup          Go To Page "javascript/alert.html"


*** Test Cases ***
Handle Alert Different Timeouts Types Str None
    Click Link    Click Me!
    Handle Alert    ACCEPT    None
    Alert Should Not Be Present

Handle Alert Different Timeouts Types Object None
    Click Link    Click Me!
    Handle Alert    ACCEPT    ${None}
    Alert Should Not Be Present

Handle Alert Different Timeouts Types Str Int
    [Documentation]    This tests the RF conversion than alters
    Click Link    Click Me!
    Handle Alert    ACCEPT    3
    Alert Should Not Be Present

Handle Alert Different Timeouts Types Str Float
    Click Link    Click Me!
    Handle Alert    ACCEPT    2.0
    Alert Should Not Be Present

Handle Alert Different Timeouts Types Float Object
    Click Link    Click Me!
    Handle Alert    ACCEPT    ${3.0}
    Alert Should Not Be Present
