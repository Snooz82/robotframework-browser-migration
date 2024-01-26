*** Settings ***
Documentation       Tests clicking element

Resource            ../resource.robot

Suite Setup         Go To Page "javascript/click.html"
Test Setup          Initialize Page


*** Test Cases ***
Click Element
    [Documentation]    LOG 1 Clicking element 'singleClickButton'.
    Click Element    singleClickButton
    Element Text Should Be    output    single clicked

Double Click Element
    [Documentation]    LOG 1 Double clicking element 'doubleClickButton'.
    [Tags]    known issue safari
    Double Click Element    doubleClickButton
    Element Text Should Be    output    double clicked

Click Element Error
    [Setup]    Go To Page "javascript/click.html"

    Run Keyword And Expect Error    Element with locator 'id:äääääää' not found.    Click Element    id:äääääää

Click Element Error 2
    [Setup]    Go To Page "javascript/click.html"
    Run Keyword And Expect Error    Element with locator 'id:鱼鱼鱼鱼' not found.    Click Element    id:鱼鱼鱼鱼

Click Element Error 3
    [Setup]    Go To Page "javascript/click.html"
    Run Keyword And Expect Error    Element with locator '鱼在天空中飞翔' not found.    Click Element    鱼在天空中飞翔

Double Click Element Error
    [Setup]    Go To Page "javascript/click.html"
    Run Keyword And Expect Error    Element with locator 'id:öööö' not found.    Double Click Element    id:öööö

Click Element Action Chain
    [Documentation]
    ...    LOB 1:1 INFO    Clicking 'singleClickButton' using an action chain.
    [Tags]    nogrid
    Click Element    singleClickButton    action_chain=True
    Element Text Should Be    output    single clicked


*** Keywords ***
Initialize Page
    [Documentation]    Initialize Page
    Reload Page
    Set Selenium Timeout    1 seconds
    Element Text Should Be    output    initial output
