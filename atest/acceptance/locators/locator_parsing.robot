*** Settings ***
Documentation       Tests different supported xpath strategies

Resource            ../resource.robot

Test Setup          Go To Page "links.html"


*** Test Cases ***
xpath with prefix should work
    Page Should Contain Element    xpath=//div[@id="div_id"]/a
    Page Should Contain Element    xpath://div[@id="div_id"]/a

xpath with // and without prefix should work
    Page Should Contain Element    //div[@id="div_id"]/a

xpath with (// and without prefix should work
    Page Should Contain Element    (//div[@id="div_id"]/a)[1]

Locator with with data prefix
    Page Should Contain Element    data:id:my_id
    Page Should Contain Element    data:automation:my_automation_id
    Page Should Not Contain Element    data:non_existent:some_random_id

Locator without prefix
    Page Should Contain Element    div_id

Locator with prefix
    Page Should Contain Element    id:div_id
    Page Should Contain Element    id=div_id
    Page Should Contain Element    id:foo:bar
    Page Should Contain Element    id=foo:bar
    Page Should Contain Element    id:bar=foo
    Page Should Contain Element    id=bar=foo

Locator with separator but without matching prefix is not special
    Page Should Contain Element    foo:bar
    Page Should Contain Element    bar=foo

Locator with separator and with matchign prefix cannot be used as-is
    Page Should Contain Element    id:id:problematic
    Page Should Contain Element    id=id:problematic
    Run Keyword And Expect Error
    ...    Page should have contained element 'id:problematic' but did not.
    ...    Page Should Contain Element    id:problematic

Multiple Locators with double arrows as separator should work
    Page Should Contain Element    css:div#div_id >> xpath:a[6] >> id:image1_id
    ${list}    Create List    css:div#div_id    xpath:a[6]    id:image1_id
    Page Should Contain Element    ${list}

Multiple Locators strategy should be case-insensitive
    Page Should Contain Element    cSs=div#div_id >> XpaTh=a[6] >> iD=image1_id

Multiple Locators as a List should work
    ${element}    Get WebElement    id:foo:bar
    ${locator_list}    Create List    ${element}    id:bar=foo
    Page Should Contain Element    ${locator_list}

Multiple Locators as a List 2 should work
    ${parent}    Get WebElement    css:div#div_id
    ${list}    Create List    ${parent}    xpath:a[6]    id:image1_id
    Page Should Contain Element    ${list}

When One Of Locator From Multiple Locators Is Not Found Keyword Fails
    [Tags]    browser:different_error
    Run Keyword And Expect Error
    ...    Page should have contained element 'css=div#div_id >> id:not_here >> iD=image1_id' but did not.
    ...    Page Should Contain Element    css=div#div_id >> id:not_here >> iD=image1_id

When One Of Locator From Multiple Locators Matches Multiple Elements Keyword Should Not Fail
    Page Should Contain Element    xpath://div >> id=image1_id
