import re
from os.path import abspath, dirname, join

from setuptools import find_packages, setup

CURDIR = dirname(abspath(__file__))

with open("README.rst", encoding="utf-8") as fh:
    long_description = fh.read()

with open(join(CURDIR, "src", "SeleniumLibraryToBrowser", "__init__.py"), encoding="utf-8") as f:
    VERSION = re.search('__version__ = "(.*)"', f.read()).group(1)

setup(
    name="robotframework-browser-migration",
    version=VERSION,
    author="René Rohner(Snooz82)",
    author_email="snooz@posteo.de",
    description="Some small helpers for migration of SeleniumLibrary to Browser",
    long_description_content_type="text/x-rst",
    long_description=long_description,
    url="https://github.com/Snooz82/robotframework-browser-migration",
    package_dir={"": "src"},
    packages=find_packages("src"),
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
        "Topic :: Software Development :: Testing",
        "Topic :: Software Development :: Testing :: Acceptance",
        "Framework :: Robot Framework",
    ],
    python_requires=">=3.6",
    install_requires=["robotframework >= 5.0"],
    entry_points={"console_scripts": ["SeleniumStats = SeleniumStats.__main__:main"]},
)
