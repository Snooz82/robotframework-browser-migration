*** Settings ***
Resource          table_resource.robot

*** Test Cases ***
Should Retrieve Text From Cell
    [Template]    Table Cell Should Be Equal
    simpleTable              1    1    simpleTable_A1
    id:simpleTable          -1   -1    simpleTable_C3
    tableWithSingleHeader    1    1    tableWithSingleHeader_A1
    tableWithSingleHeader    3    3    tableWithSingleHeader_C3
    css:#withHeadAndFoot     1    2    withHeadAndFoot_BH1
    withHeadAndFoot          4    3    withHeadAndFoot_C2
    withHeadAndFoot          6    1    withHeadAndFoot_AF1
    withHeadAndFoot         -2   -3    withHeadAndFoot_AF1
    mergedRows               2    1    mergedRows_B2
    mergedCols               1    2    mergedCols_C1
    formattedTable           1    1    formattedTable_A1
    formattedTable           1    4    formattedTable_D1
    formattedTable           2    2    formattedTable_B2
    formattedTable           2    3    formattedTable_ÄÖÜäöüß
    formattedTable           2    4    äöü€&äöü€&

Mixed th and td
    [Template]    Table Cell Should Be Equal
    mixed-th-td              1    1    1.1 (th)
    id:mixed-th-td           1    2    1.2 (td)
    css:#mixed-th-td         1    3    1.3 (td)
    //*[@id="mixed-th-td"]   2    2    2.2 (th)
    mixed-th-td              3    2    3.2 (td)
    mixed-th-td              4    2    4.2 (th)
    mixed-th-td              5    2    5.2 (td)
    mixed-th-td              6    2    6.2 (th)
    mixed-th-td             -1   -1    6.3 (th)
    mixed-th-td             -1   -2    6.2 (th)
    mixed-th-td             -1   -3    6.1 (td)
    mixed-th-td             -6   -3    1.1 (th)
    mixed-th-td             -6   -2    1.2 (td)
    mixed-th-td             -6   -1    1.3 (td)

Should Give Error Message When Content Not Found In Table Cell
    Run Keyword And Expect Error
    ...    *
    ...    Table Cell Should Contain    simpleTable    1    2    simpleTable_B3

Should Give Error Message When Index Out Of Bounds
    Run Keyword And Expect Error
    ...    *
    ...    Table Cell Should Contain    simpleTable    10    20    simpleTable_B3
    Run Keyword And Expect Error
    ...    *
    ...    Table Cell Should Contain    simpleTable    1    20    simpleTable_B3

Zero is invalid row and column index
    Run Keyword And Expect Error
    ...    *
    ...    Table Cell Should Contain    simpleTable    0    2    xxx
    Run Keyword And Expect Error
    ...    *
    ...    Table Cell Should Contain    simpleTable    -1    0    xxx

*** Keywords ***
Table Cell Should Be Equal
    [Arguments]    ${tableId}    ${row}    ${col}    ${content}
    ${cell}=    Get Table Cell    ${tableId}    ${row}    ${col}
    Should Be Equal    ${cell}    ${content}
