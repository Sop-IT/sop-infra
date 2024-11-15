#!/bin/bash

# move to netbox repo
cd netbox/

# add local_requirements
cat << EOF >> local_requirements.txt
django-test-without-migrations
EOF

# add testing configuration
cp netbox/netbox/configuration_example.py netbox/netbox/configuration.py
secret_key="$(python3 netbox/generate_secret_key.py)"
allowed_hosts="'*'"
cat << EOF >> netbox/netbox/configuration.py
ALLOWED_HOSTS = [$allowed_hosts]
DATABASE = {
 'ENGINE': 'django.db.backends.postgresql',
 'NAME': 'netbox',
 'USER': 'netbox',
 'PASSWORD': 'salut',
 'HOST': 'localhost',
 'PORT': '',
 'CONN_MAX_AGE': 300,
}
SECRET_KEY = '$secret_key'
PLUGINS = ['sop_infra']
PLUGINS_CONFIG = {
    'sop_infra': {
        'panels': ['meraki', 'classification', 'sizing'],
        'display_default': 'left_page',
        'display_custom': {'sizing':'right_page'}
    }
}
EOF

sed -i "/INSTALLED_APPS = \[/a\    'test_without_migrations'," "netbox/netbox/settings.py"

# creates venv
python3 -m venv venv
source venv/bin/activate

# recursive install packages
pip install --upgrade pip
pip install wheel
pip install -r requirements.txt
pip install -r local_requirements.txt

# apply migration
python3 netbox/manage.py migrate

# collecting statings
python3 netbox/manage.py collectstatic --no-input

# reindex
python3 netbox/manage.py reindex --lazy

