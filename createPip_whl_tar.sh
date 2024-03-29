#!/bin/zsh
libdoc SeleniumLibraryToBrowser doc/index.html
surge doc robotframework-browser-migration.surge.sh
check-manifest --update
rm -f dist/*.*
python setup.py bdist_wheel sdist
twine check dist/*
echo "Next step - uploading to pypi!"
read -n 1
twine upload dist/*
