*** Settings ***
Resource            resource.robot
Library             ExtSL.ExtSL    WITH NAME    ExtSeLib

Suite Setup         Extending Suite Setup
Suite Teardown      ExtSeLib.Close All Browsers

Test Tags           robot:skip


*** Test Cases ***
When Extending SeleniumLibrary Keywords With Decorated Name Can Be Used For Extending
    ${elements} =    ExtSeLib.Ext Web Element    //tr
    Should Not Be Empty    ${elements}

When Extending SeleniumLibrary Keywords With Method Name Can Be Used For Extending
    ExtSeLib.Ext Page Should Contain    Email:


*** Keywords ***
Extending Suite Setup
    ExtSeLib.Open Browser    ${ROOT}/forms/prefilled_email_form.html    ${BROWSER}
