#!/bin/bash

export TWINE_USERNAME="$pypi_name"
export TWINE_PASSWORD="$infra_api"

python3 setup.py sdist bdist_wheel
twine upload --skip-existing --verbose dist/*

#_________________________________
# if twine doesn't work, rerun with
# --skip-existing argument
