*** Settings ***
Documentation       Tests mouse

Resource            ../resource.robot

Test Setup          Go To Page "mouse/index.html"

Test Tags           known issue internet explorer


*** Test Cases ***
Mouse Over
    [Tags]    known issue safari
    Mouse Over    el_for_mouseover
    Textfield Value Should Be    el_for_mouseover    mouseover el_for_mouseover
    Run Keyword And Expect Error
    ...    Element with locator 'not_there' not found.
    ...    Mouse Over    not_there

Mouse Over Error
    [Tags]    known issue safari
    Mouse Over    el_for_mouseover
    Textfield Value Should Be    el_for_mouseover    mouseover el_for_mouseover
    Run Keyword And Expect Error
    ...    Element with locator '鱼在天空中飞翔' not found.
    ...    Mouse Over    鱼在天空中飞翔

Mouse Out
    [Tags]    known issue safari
    Mouse Out    el_for_mouseout
    Textfield Value Should Be    el_for_mouseout    mouseout el_for_mouseout
    Run Keyword And Expect Error
    ...    Element with locator 'not_there' not found.
    ...    Mouse Out    not_there

Mouse Down
    [Tags]    known issue safari
    Mouse Down    el_for_mousedown
    Textfield Value Should Be    el_for_mousedown    mousedown el_for_mousedown
    Run Keyword And Expect Error
    ...    Element with locator 'not_there' not found.
    ...    Mouse Down    not_there

Mouse Up
    [Tags]    known issue safari    known issue firefox
    Mouse Up    el_for_mouseup
    Textfield Value Should Be    el_for_mouseup    mouseup el_for_mouseup
    Run Keyword And Expect Error
    ...    Element with locator 'not_there' not found.
    ...    Mouse Up    not_there

Simulate Event
    Simulate event    el_for_blur    blur
    Textfield Value Should Be    el_for_blur    blur el_for_blur
