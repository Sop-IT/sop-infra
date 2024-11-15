#!/bin/bash

cd netbox/
source venv/bin/activate
python3 netbox/manage.py test -n sop_infra.tests


