# NetBox - Sop-Infra plugin

> [NetBox](https://github.com/netbox-community/netbox) plugin to manage infrastructure informations of each site.

## Installation

### Auto-upgrade installation

Add the plugin to NetBox local_requirements
```bash
echo -e "sop_infra" >> local_requirements.txt
```

Add the plugin to netbox/configuration.py
```python
PLUGINS = [
    ...
    'sop_infra',
]
```

Run NetBox upgrade.sh script
```bash
sudo ./upgrade.sh
```

## Features

This plugin provides the following features:
-   Add a new "**Infrastructure**" tab in */dcim/sites/your_site_id*
