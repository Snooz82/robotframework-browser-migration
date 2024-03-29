*** Settings ***
Resource        ../resource.robot

Test Setup      Go To Page "javascript/delayed_events.html"

Test Tags       known issue internet explorer


*** Test Cases ***
Wait For Condition
    Title Should Be    Original
    Wait For Condition    return window.document.title == "Changed"
    Run Keyword And Expect Error
    ...    Condition 'return window.document.title == "Invalid"' did not become true in 100 milliseconds.
    ...    Wait For Condition    return window.document.title == "Invalid"    ${0.1}

Wait For Condition Comlext Wait
    Wait For Condition
    ...    style = document.querySelector('#content').style; return style.background == 'red' && style.color == 'white'

Wait For Condition requires `return`
    Run Keyword And Expect Error
    ...    ValueError: Condition 'window.document.title == "Changed"' did not have mandatory 'return'.
    ...    Wait For Condition    window.document.title == "Changed"

Wait Until Page Contains
    Wait Until Page Contains    New Content    2 s
    Run Keyword And Expect Error
    ...    Text 'invalid' did not appear in 100 milliseconds.
    ...    Wait Until Page Contains    invalid    0.1

Wait Until Page Does Not Contain
    Wait Until Page Does Not Contain    This is content    2 s
    Run Keyword And Expect Error
    ...    Text 'Initially hidden' did not disappear in 100 milliseconds.
    ...    Wait Until Page Does Not Contain    Initially hidden    0.1

Wait Until Page Contains Element
    [Documentation]    Tests also that format characters (e.g. %c) are handled correctly in error messages
    Wait Until Page Contains Element    new div    2 seconds
    Run Keyword And Expect Error
    ...    Element '%cnon-existent' did not appear in 100 milliseconds.
    ...    Wait Until Page Contains Element    %cnon-existent    0.1 seconds
    Run Keyword And Expect Error
    ...    Element 'id:ääööåå' did not appear in 100 milliseconds.
    ...    Wait Until Page Contains Element    id:ääööåå    0.1 seconds

Wait Until Page Contains Element Limit No Elements
    Run Keyword And Expect Error
    ...    Page should have contained "5" %cnon-existent element(s) within 100 milliseconds.
    ...    Wait Until Page Contains Element    %cnon-existent    0.1 seconds    limit=5

Wait Until Page Contains Element Limit Too Few Elements
    Run Keyword And Expect Error
    ...    Page should have contained "10" //div element(s) within 100 milliseconds.
    ...    Wait Until Page Contains Element    //div    0.1 seconds    limit=10

Wait Until Page Contains Element Limit Too Many Elements
    Run Keyword And Expect Error
    ...    Page should have contained "1" //div element(s) within 100 milliseconds.
    ...    Wait Until Page Contains Element    //div    0.1 seconds    limit=1

Wait Until Page Contains Element Limit Zero Elements And Zero Required
    Wait Until Page Contains Element    //divNotExists    0.1 seconds    limit=0

Wait Until Page Contains Element Limit With Negative Limit
    Run Keyword And Expect Error
    ...    Page should have contained "-1" //divNotExists element(s) within 100 milliseconds.
    ...    Wait Until Page Contains Element    //divNotExists    0.1 seconds    limit=-1

Wait Until Page Contains Element Limit
    Wait Until Page Contains Element    new div    2 seconds    limit=1

Wait Until Page Does Not Contain Element
    Wait Until Page Does Not Contain Element    not_present    2 seconds
    Run Keyword And Expect Error
    ...    Element 'content' did not disappear in 100 milliseconds.
    ...    Wait Until Page Does Not Contain Element    content    0.1 seconds
    Run Keyword And Expect Error
    ...    Custom Error ää ÖÖ
    ...    Wait Until Page Does Not Contain Element    content    0.1 seconds    Custom Error ää ÖÖ

Wait Until Page Does Not Contain Element Limit Not Found
    Wait Until Page Does Not Contain Element    //div    0.1 seconds    limit=4

Wait Until Page Does Not Contain Element Limit Found
    Run Keyword And Expect Error
    ...    Page should have not contained "5" //div element(s) within 100 milliseconds.
    ...    Wait Until Page Does Not Contain Element    //div    0.1 seconds    limit=5

Wait Until Page Does Not Contain Element Limit Negative Limit
    Wait Until Page Does Not Contain Element    not_present    0.1 seconds    limit=-1

Wait Until Page Does Not Contain Element Limit As Zero
    Wait Until Page Does Not Contain Element    not_present    0.1 seconds    limit=0

Wait Until Element Is Enabled
    Run Keyword And Expect Error
    ...    Element 'id=disabled' was not enabled in 2 milliseconds.
    ...    Wait Until Element Is Enabled    id=disabled    2ms
    Run Keyword And Expect Error
    ...    User error message
    ...    Wait Until Element Is Enabled    id=disabled    0.003    User error message
    Wait Until Element Is Enabled    id=disabled    2 s
    Run Keyword And Expect Error
    ...    Element with locator 'id=invalid' not found.
    ...    Wait Until Element Is Enabled    id=invalid    0.1

Wait Until Element Is Enabled with readonly element
    Run Keyword And Expect Error
    ...    Element 'readonly' was not enabled in 2 milliseconds.
    ...    Wait Until Element Is Enabled    readonly    2ms
    Wait Until Element Is Enabled    readonly    2 s

Wait Until Element Contains
    Run Keyword And Expect Error
    ...    Element 'id=content' did not get text 'New' in 1 millisecond.
    ...    Wait Until Element Contains    id=content    New    0.001
    Run Keyword And Expect Error
    ...    User error message
    ...    Wait Until Element Contains    id=content    New    99ms    User error message
    Wait Until Element Contains    content    New Content    2 s
    Wait Until Element Contains    content    New    2 s
    Run Keyword And Expect Error
    ...    User error message    Wait Until Element Contains
    ...    content    Error    0.1    User error message

Wait Until Element Does Not Contain
    Run Keyword And Expect Error
    ...    Element 'id=content' still had text 'This is' after 100 milliseconds.
    ...    Wait Until Element Does Not Contain    id=content    This is    0.1
    Wait Until Element Does Not Contain    content    This is    2 s
    Wait Until Element Does Not Contain    id=content    content    2 s
    Run Keyword And Expect Error
    ...    User error message
    ...    Wait Until Element Does Not Contain    content    New Content    0.1    User error message

Timeout can be zero
    Run Keyword And Expect Error
    ...    Element 'content' did not get text 'New Content' in 0 seconds.
    ...    Wait Until Element Contains    content    New Content    0
    Run Keyword And Expect Error
    ...    Element 'content' did not get text 'New Content' in 0 seconds.
    ...    Wait Until Element Contains    content    New Content    ${0}
