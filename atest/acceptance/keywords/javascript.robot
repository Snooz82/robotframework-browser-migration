*** Settings ***
Resource        ../resource.robot

Test Setup      Go To Page "javascript/dynamic_content.html"


*** Test Cases ***
Clicking Elements Should Activate Javascript
    Title Should Be    Original
    Click Element    link=change title
    Title Should Be    Changed

Mouse Down On Link
    [Tags]    known issue safari
    [Setup]    Go To Page "javascript/mouse_events.html"
    Mouse Down On Image    image_mousedown
    Text Field Should Contain    textfield    onmousedown
    Mouse Up    image_mousedown
    Input text    textfield    ${EMPTY}
    Mouse Down On Link    link_mousedown
    Text Field Should Contain    textfield    onmousedown
    Mouse Up    link_mousedown

Execute Javascript
    Execute Javascript    window.add_content('button_target', 'Inserted directly')
    Page Should Contain    Inserted directly

Execute Javascript With ARGUMENTS and JAVASCRIPT Marker
    ${l}=    Create List    one    two    three
    ${result}=    Execute Javascript
    ...    ARGUMENTS
    ...    ${l}
    ...    ${l}
    ...    JAVASCRIPT
    ...    return [arguments[0][2], arguments[0][1]];
    Should Be Equal    ${result}    ${{["three", "two"]}}

Execute Javascript With JAVASCRIPT and ARGUMENTS Marker
    ${l}=    Create List    one    two    three
    ${result}=    Execute Javascript
    ...    JAVASCRIPT
    ...    return [arguments[0][2], arguments[0][1]];
    ...    ARGUMENTS
    ...    ${l}
    ...    ${l}
    Should Be Equal    ${result}    ${{["three", "two"]}}

Execute Javascript With ARGUMENTS Marker Only
    ${l}=    Create List    one    two    three
    ${result}=    Execute Javascript
    ...    return [arguments[0][2], arguments[0][1]];
    ...    ARGUMENTS
    ...    ${l}
    ...    ${l}
    Should Be Equal    ${result}    ${{["three", "two"]}}

Execute Javascript With ARGUMENTS Marker And WebElement
    ${body_webelement}=    Get WebElement    css:body
    ${tag_name}=    Execute Javascript
    ...    return arguments[0].tagName;
    ...    ARGUMENTS
    ...    ${body_webelement}
    Should Be Equal As Strings    ${tag_name}    body    ignore_case=True

Execute Javascript from File
    [Documentation]
    ...    LOG 1:1 REGEXP: Reading JavaScript from file .*executed_by_execute_javascript.*
    ...    LOG 1:2 Executing JavaScript:
    ...    window.add_content('button_target', 'Inserted via file')
    ...    Without any arguments.
    Execute Javascript    ${CURDIR}/executed_by_execute_javascript.js
    Page Should Contain    Inserted via file

Execute Javascript from File With ARGUMENTS Marker
    ${l}=    Create List    one    two    three
    ${result}=    Execute Javascript
    ...    ${CURDIR}/javascript_alert.js
    ...    ARGUMENTS
    ...    ${l}
    ...    ${l}
    Should Be Equal    ${result}    ${{["three", "two"]}}

Execute Javascript with dictionary object
    &{ARGS}=    Create Dictionary    key=value    number=${1}    boolean=${TRUE}
    ${returned}=    Execute JavaScript    return arguments[0]    ARGUMENTS    ${ARGS}
    Should Be True    type($returned) == dict
    Should Be Equal    ${returned}[key]    value
    Should Be Equal    ${returned}[number]    ${1}
    Should Be Equal    ${returned}[boolean]    ${TRUE}

Open Context Menu
    [Tags]    known issue safari
    Go To Page "javascript/context_menu.html"
    Open Context Menu    myDiv

Drag and Drop
    [Tags]    known issue internet explorer    known issue safari
    [Setup]    Go To Page "javascript/drag_and_drop.html"
    Element Text Should Be    id=droppable    Drop here
    Drag and Drop    id=draggable    id=droppable
    Element Text Should Be    id=droppable    Dropped!

Drag and Drop by Offset
    [Tags]    known issue internet explorer    known issue safari
    [Setup]    Go To Page "javascript/drag_and_drop.html"
    Element Text Should Be    id=droppable    Drop here
    Drag and Drop by Offset    id=draggable    ${1}    ${1}
    Element Text Should Be    id=droppable    Drop here
    Drag and Drop by Offset    id=draggable    ${100}    ${20}
    Element Text Should Be    id=droppable    Dropped!
