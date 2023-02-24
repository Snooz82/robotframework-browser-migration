*** Settings ***
Documentation     Tests mouse
Test Setup        Go To Page "mouse/index.html"
Force Tags        Known Issue Internet Explorer
Resource          ../resource.robot

*** Test Cases ***
Mouse Over
    [Tags]    Known Issue Safari
    Mouse Over    el_for_mouseover
    Textfield Value Should Be    el_for_mouseover    mouseover el_for_mouseover
    Run Keyword And Expect Error
    ...    *
    ...    Mouse Over    not_there

Mouse Over Error
    [Tags]    Known Issue Safari
    Mouse Over    el_for_mouseover
    Textfield Value Should Be    el_for_mouseover    mouseover el_for_mouseover
    Run Keyword And Expect Error
    ...    *
    ...    Mouse Over    鱼在天空中飞翔

Mouse Out
    [Tags]    Known Issue Safari
    Mouse Out    el_for_mouseout
    Textfield Value Should Be    el_for_mouseout    mouseout el_for_mouseout
    Run Keyword And Expect Error
    ...    *
    ...    Mouse Out    not_there

Mouse Down
    [Tags]    Known Issue Safari
    Mouse Down    el_for_mousedown
    Textfield Value Should Be    el_for_mousedown    mousedown el_for_mousedown
    Run Keyword And Expect Error
    ...    *
    ...    Mouse Down    not_there

Mouse Up
    [Tags]    Known Issue Safari    Known Issue Firefox
    Mouse Up    el_for_mouseup
    Textfield Value Should Be    el_for_mouseup    mouseup el_for_mouseup
    Run Keyword And Expect Error
    ...    *
    ...    Mouse Up    not_there

Simulate Event
    [Tags]    NotImplemented
    Simulate event    el_for_blur    blur
    Textfield Value Should Be    el_for_blur    blur el_for_blur
