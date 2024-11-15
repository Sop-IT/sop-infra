#!/bin/bash

# install postgresql
sudo apt install -y postgresql
sudo systemctl enable --now postgresql
# create psql test db
sudo -u postgres psql -c "CREATE DATABASE netbox;"
sudo -u postgres psql -c "CREATE USER netbox WITH PASSWORD 'salut';"
sudo -u postgres psql -c "ALTER DATABASE netbox OWNER TO netbox;"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE netbox TO netbox;"
sudo -u postgres psql -c "GRANT CREATE ON SCHEMA public TO netbox;"
sudo -u postgres psql -c "ALTER USER netbox CREATEDB;"

# install redis
sudo apt install -y redis-server
sudo systemctl enable --now redis

# install netbox dependencies
sudo apt install -y python3 python3-pip python3-venv python3-dev build-essential libxml2-dev libxslt1-dev libffi-dev libpq-dev libssl-dev zlib1g-dev

