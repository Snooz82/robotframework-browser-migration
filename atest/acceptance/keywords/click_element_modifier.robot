*** Settings ***
Test Setup       Go To Page "javascript/click_modifier.html"
Resource          ../resource.robot

*** Test Cases ***
Click Link Modifier Shift
    Click Link    link text    modifier=Shift
    Element Text Should Be    output    Shift click

Click Button Modifier Shift
    Click Button    Click me!    modifier=Shift
    Element Text Should Be    output    Shift click

Click Image Modifier Shift
    Click Image    robot    modifier=Shift
    Element Text Should Be    output    Shift click

Click Element Modifier ALT
    Click Element    Button    alt
    Element Text Should Be    output    ALT click

Click Element Modifier Shift
    Click Element    Button    Shift
    Element Text Should Be    output    Shift click

Click Element Modifier Shift+Shift
    [Tags]    NotRelevant   andWTF
    Click Element    Button    modifier=Shift+Shift
    Element Text Should Be    output    Shift and Shift click

Click Element No Modifier
    Click Element    Button    modifier=False
    Element Text Should Be    output    Normal click

Click Element Wrong Modifier
    Run Keyword And Expect Error
    ...    *
    ...    Click Element    Button    Foobar

Click Element Action Chain and modifier
    [Documentation]     LOG 1:1 INFO Clicking element 'Button' with CTRL.
    Click Element    Button    modifier=Shift    action_chain=True
    Element Text Should Be    output    Shift click

*** Keywords ***
Initialize Page
    Reload Page
    Element Text Should Be    output    initial output

Close Popup Window
    Switch Window    myName    timeout=5s
    Close Window
    Switch Window    MAIN      timeout=5s
