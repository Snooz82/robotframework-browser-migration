*** Settings ***
Documentation       Creating test which would work on all browser is not possible. When testing with other
...                 browser than Chrome it is OK that these test will fail. SeleniumLibrary CI is run with Chrome only
...                 and therefore there is tests for Chrome only.
...                 Also it is hard to create where chromedriver location would suite in all os and enviroments, therefore
...                 there is a test which tests error scenario and other scenarios needed manual or unit level tests

Resource            resource.robot

Suite Teardown      Close All Browsers


*** Test Cases ***
Chrome Browser With executable_path Argument
    [Tags]    nogrid    triage
    Run Keyword And Expect Error
    ...    Error: browserType.launchPersistentContext: Failed to launch chromium because executable doesn't exist at /does/not/exist
    ...    Open Browser
    ...    ${FRONT PAGE}
    ...    ${BROWSER}
    ...    remote_url=${REMOTE_URL}
    ...    desired_capabilities=${DESIRED_CAPABILITIES}
    ...    executable_path=/does/not/exist
