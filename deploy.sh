#!/bin/bash

python3 setup.py sdist bdist_wheel
twine upload --verbose dist/*

#_________________________________
# if twine doesn't work, rerun with
# --skip-existing argument
