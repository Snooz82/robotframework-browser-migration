===================================================
robotframework-browser-migration
===================================================


This project contains two things.

1. A small script to analyze your SeleniumLibrary keywords unsed and create a statistic over
   the usage in your project.
2. A migration layer library named `SeleniumLibraryToBrowser` that has ~80% of the SeleniumLibrary keywords implemented by Browser library.


Installation
------------

run:

``pip install robotframework-browser-migration``

for the migration layer library you also need Robot_Framework_Browser_ installed and initialized as well:

``pip install robotframework-browser``

and

``rfbrowser init``

.. _Robot_Framework_Browser: https://browserlibrary.org

|

===================================================
SeleniumLibraryToBrowser
===================================================

Please find the implemented keywords here in the Keyword_Documentation_.

.. _Keyword_Documentation: https://snooz82.github.io/robotframework-browser-migration/?tag=IMPLEMENTED

Usage:


.. code:: robotframework

    *** Settings ***
    Library  SeleniumLibraryToBrowser

    *** Test Cases ***
    My Test Case
        Open Browser  https://robocon.io  chrome
        Location Should Be     https://robocon.io/
        ${hamburger}=    Run Keyword And Return Status    Element Should Be Visible    css:.hamburger
        IF    ${hamburger}     Click Button    css:.hamburger
        Click Link     RBCN22
        Location Should Be     https://robocon.io/2022
        Close All Browsers


Be aware that some keywords will never be implemented and others are just barely compatible.
Like ``Open Browser`` is really recommented to use the Browser library ``New Browser/New Context/New Page`` or ``New Persistent Context`` instead.


===================================================
SeleniumStats
===================================================

We want to know which keywords are massively used in our community.
In the first step we would like to get this information to know which keywords are missing
in Browser Library.

Later we also will show you which of your keywords are already replaceable by Browser and
how to do so.

We appreciate your help!

|

How it works
------------

This small script analyzes your output.xml and creates a statistic over the usage of your
SeleniumLibrary Keywords.

It will check which Selenium Keywords are used, and how often they are called in general.
It also check how many different parents (Keywords, TestCases or TestSuites) calls this keyword
directly. This "parent" count is the number of places you may have to change when migrating later.

We never ever ever take any of your private or confidential data!
We also just uses hashes of the names of your
Tests and Keywords to sum up their appearance.
And also these hashes are never ever stored in any file.

The generated data/statistic are absolutely anonymous!

You will see all collected data as a statistics table when finished.

Like here:

.. code-block::

    +----------------------------------+-------+---------+
    | Keyword                          | count | parents |
    +----------------------------------+-------+---------+
    | Checkbox Should Be Selected      | 10    | 2       |
    | Checkbox Should Not Be Selected  | 10    | 2       |
    | Clear Element Text               | 1     | 1       |
    | Click Button                     | 4     | 4       |
    | Click Element                    | 48    | 20      |
    | Click Link                       | 18    | 10      |
    | Close All Browsers               | 30    | 16      |
    | Close Browser                    | 15    | 8       |
    | Element Text Should Be           | 18    | 5       |
    | Execute Javascript               | 18    | 2       |
    | Get Element Count                | 8     | 1       |
    | Get Location                     | 8     | 2       |
    | Get Text                         | 40    | 9       |
    | Get WebElement                   | 17    | 3       |
    | Get WebElements                  | 10    | 3       |
    | Go To                            | 30    | 19      |
    | Input Password                   | 45    | 19      |
    | Input Text                       | 47    | 21      |
    | Location Should Be               | 47    | 16      |
    | Open Browser                     | 55    | 29      |
    | Page Should Contain Element      | 9     | 8       |
    | Select Checkbox                  | 10    | 4       |
    | Select From List By Label        | 2     | 2       |
    | Select From List By Value        | 1     | 1       |
    | Set Window Position              | 2     | 2       |
    | Switch Window                    | 16    | 1       |
    | Title Should Be                  | 30    | 16      |
    | Unselect Checkbox                | 8     | 4       |
    | Wait Until Element Is Visible    | 27    | 9       |
    | Wait Until Page Contains Element | 4     | 1       |
    +----------------------------------+-------+---------+

    Statistics File: /Source/robotframework-browser-migration/src/keyword_stats.json
    Please upload the file to https://data.keyword-driven.de/index.php/s/SeleniumStats for full anonymity.
    IP-Addresses or other personal data are not logged when uploading the file!
    You can also mail it to mailto:rene@robotframework.org.

    Thanks you very much for your support!
    Your Browser-Team (Mikko, Tatu, Kerkko, Janne and René)

The easiest and most anonymous way to share these data with us, would be to upload the
``keyword_stats.json`` to https://data.keyword-driven.de/index.php/s/SeleniumStats .
We do not store any information of the one who uploaded it. No IP-Address! Nothing.


|

Usage
~~~~~

Call the SeleniumStats with the path to your ``output.xml`` as first argument.
The ``output.xml`` can also be from a dryrun!

``python -m SeleniumStats c:\\MyTests\\output.xml``

Then send us the ``keyword_stats.json`` please.

|

Thank you very much!!!
----------------------
The Browser-Team

