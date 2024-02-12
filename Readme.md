# robotframework-browser-migration


This project contains two things.

1. A compatibility/migration layer library named _**SeleniumLibraryToBrowser**_ that has 164 of the 177 [SeleniumLibrary](https://github.com/robotframework/SeleniumLibrary) keywords implemented by using [Browser](https://browserlibrary.org) library internally. See [SeleniumLibraryToBrowser Keyword Documentation](https://snooz82.github.io/robotframework-browser-migration/).
2. A script to analyzes your [SeleniumLibrary](https://github.com/robotframework/SeleniumLibrary) keywords usage and creates a statistic over
   the usage in your project to get an impression of the effort when a migration to [Browser](https://browserlibrary.org) library is the goal.


## Installation

run:

`pip install robotframework-browser-migration`

for the migration layer library _**SeleniumLibraryToBrowser**_ or if you want the information which keyword is supported by it, you also need [Robot Framework Browser](https://browserlibrary.org) installed and initialized as well:

`pip install robotframework-browser`

and

`rfbrowser init`


# SeleniumLibraryToBrowser


## Overview

_**SeleniumLibraryToBrowser**_ is an innovative project designed to bridge the gap between two prominent libraries in the
Robot Framework community: [SeleniumLibrary](https://robotframework.org/SeleniumLibrary) and
[Browser](https://robotframework-browser.org) library. This library is crafted to facilitate a smooth transition for users who
wish to upgrade their web automation capabilities by leveraging the advanced features of the 
[Browser](https://robotframework-browser.org) library, while maintaining compatibility with the existing keyword design of
[SeleniumLibrary](https://robotframework.org/SeleniumLibrary).

## Purpose

The primary objective of _**SeleniumLibraryToBrowser**_ is to enable seamless migration from 
[SeleniumLibrary](https://robotframework.org/SeleniumLibrary) to [Browser](https://robotframework-browser.org) library without
the need for extensive rewrites of existing test suites and high-level keywords. It recognizes the significant investment users have made in 
[SeleniumLibrary](https://robotframework.org/SeleniumLibrary) and respects the history and value it has brought to the 
Robot Framework community. This library is not intended as a replacement for 
[SeleniumLibrary](https://robotframework.org/SeleniumLibrary), but as a complementary tool that offers additional options 
and flexibility for test automation.

## Key Features

### Compatibility with [SeleniumLibrary](https://robotframework.org/SeleniumLibrary) Keywords:
_**SeleniumLibraryToBrowser**_ allows existing test scripts, which use [SeleniumLibrary](https://robotframework.org/SeleniumLibrary)
keywords, to function with minimal changes, thereby reducing migration effort and time.

### Leveraging [Browser](https://robotframework-browser.org) Library Advantages:
Users can benefit from the speed, stability, and modern web technology support of the 
[Browser](https://robotframework-browser.org) library, especially in handling complex elements like WebComponents and ShadowDOM.

### Coexistence and Support:
This project emphasizes the coexistence and mutual respect between [SeleniumLibrary](https://robotframework.org/SeleniumLibrary)
and [Browser](https://robotframework-browser.org) library. It is not a hostile takeover but a supportive extension,
offering more choices to the Robot Framework community.

## Usage Scenario

_**SeleniumLibraryToBrowser**_ is ideal for teams and projects that have an extensive codebase using [SeleniumLibrary](https://robotframework.org/SeleniumLibrary) and are seeking to upgrade to the [Browser](https://robotframework-browser.org) library's advanced features without disrupting their existing test automation infrastructure. It is particularly beneficial for those who aim to gradually transition to the [Browser](https://robotframework-browser.org) library while continuing to develop and maintain their current test suites.

## Importing the Library

To use _**SeleniumLibraryToBrowser**_ in your Robot Framework projects, you can replace the import of `SeleniumLibrary` with `SeleniumLibraryToBrowser`.
Below is an example of how to import the library:

```robotframework
*** Settings ***

Library    SeleniumLibraryToBrowser
```

This simple example may probably not be sufficient in practice.
More configs may be needed and if Browser keywords should be used as well, this library should be imported before as well.
Please see [Migration Guide](https://snooz82.github.io/robotframework-browser-migration/?tag=IMPLEMENTED#Migration%20Guide)
for more details on how to use the library.

## Configuration

Upon import, _**SeleniumLibraryToBrowser**_ initializes with default settings that ensure compatibility with [SeleniumLibrary](https://robotframework.org/SeleniumLibrary) keywords. However, users can configure it to take advantage of specific features of the [Browser](https://robotframework-browser.org) library as needed. See [Importing Section](https://snooz82.github.io/robotframework-browser-migration/?tag=IMPLEMENTED#Importing) in keyword docs.

## Conclusion

_**SeleniumLibraryToBrowser**_ represents a thoughtful and user-centric approach to evolving test automation practices within the Robot Framework community. It respects the legacy of [SeleniumLibrary](https://robotframework.org/SeleniumLibrary) while embracing the future potential of the [Browser](https://robotframework-browser.org) library, offering a balanced solution for users at different stages of their automation journey.


# SeleniumStats

We want to know which keywords are massively used in our community.
In the first step we would like to get this information to know which keywords are missing
in Browser Library.

Later we also will show you which of your keywords are already replaceable by Browser and
how to do so.

We appreciate your help!

## How it works

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

```
+------------------------------------------+-------+---------+------------------+
| Keyword                                  | count | parents | migration status |
+------------------------------------------+-------+---------+------------------+
| Add Cookie                               | 62    | 6       |                  |
| Add Location Strategy                    | 6     | 2       | missing          |
| Alert Should Be Present                  | 19    | 15      | missing          |
| Assign Id To Element                     | 1     | 1       |                  |
| Capture Page Screenshot                  | 24    | 17      |                  |
| Checkbox Should Be Selected              | 6     | 4       |                  |
| Choose File                              | 4     | 4       |                  |
| Click Element                            | 41    | 40      |                  |
| Click Link                               | 45    | 40      |                  |
| Close All Browsers                       | 22    | 22      |                  |
| Close Browser                            | 11    | 8       |                  |
| Close Window                             | 11    | 11      |                  |
| Create Webdriver                         | 4     | 3       | missing          |
| Drag And Drop                            | 1     | 1       |                  |
| Element Should Be Visible                | 4     | 4       |                  |
| Element Should Contain                   | 10    | 5       |                  |
| Element Text Should Be                   | 38    | 20      |                  |
| Execute Async Javascript                 | 18    | 11      | missing          |
| Execute Javascript                       | 13    | 11      |                  |
| Get Browser Aliases                      | 2     | 1       |                  |
| Get Element Attribute                    | 6     | 2       |                  |
| Get Element Count                        | 7     | 6       |                  |
| Get Element Size                         | 3     | 3       |                  |
| Get Location                             | 2     | 2       |                  |
| Get Text                                 | 2     | 2       |                  |
| Get Title                                | 1     | 1       |                  |
| Get WebElement                           | 9     | 9       |                  |
| Get WebElements                          | 4     | 4       |                  |
| Get Window Size                          | 4     | 4       |                  |
| Get Window Titles                        | 14    | 7       |                  |
| Go Back                                  | 1     | 1       |                  |
| Go To                                    | 370   | 41      |                  |
...
...
...
| Wait Until Location Does Not Contain     | 7     | 2       |                  |
| Wait Until Location Is                   | 3     | 2       |                  |
| Wait Until Location Is Not               | 4     | 2       |                  |
| Wait Until Page Contains                 | 17    | 17      |                  |
| Wait Until Page Contains Element         | 13    | 6       |                  |
| Wait Until Page Does Not Contain         | 2     | 2       |                  |
| Wait Until Page Does Not Contain Element | 7     | 5       |                  |
+------------------------------------------+-------+---------+------------------+

Statistics File: /System/Volumes/Data/Source/Snooz82/robotframework-browser-migration/keyword_stats.json
Please upload the file to https://data.keyword-driven.de/index.php/s/SeleniumStats for full anonymity.
IP-Addresses or other personal data are not logged when uploading the file!
You can also mail it to mailto:rene@robotframework.org.

Thank you very much for your support!
Your Browser-Team (Mikko, Tatu, Kerkko, Janne and René)
```

The easiest and most anonymous way to share these data with us, would be to upload the
`keyword_stats.json` to https://data.keyword-driven.de/index.php/s/SeleniumStats .
We do not store any information of the one who uploaded it. No IP-Address! Nothing.

## Usage

Call the SeleniumStats with the path to your `output.xml` as first argument.
The `output.xml` can also be from a dryrun!

`SeleniumStats c:/MyTests/output.xml`

Then send us the `keyword_stats.json` please.



# Thank you very much!!!
The Browser-Team


## Special Thanks

First i want to thank all contributors of SeleniumLibrary, who ensured maintenance and development of this library for years.
Specifially i want to thank [Tatu Aalto](https://github.com/aaltat) and [Ed Manlove](https://github.com/emanlove) for their work on SeleniumLibrary.

I also want to thank the [Robot Framework Foundation](https://robotframework.org/foundation/) for their support and the
funding that made it possible to bring this project to this point.
