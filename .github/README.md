# SOP-Infra

[Netbox](https://github.com/netbox-community/netbox) plugin to manage infrastructure informations of each site.

## Compatibility
NetBox >= 4.1.0

## Installation

Install the plugin as a PyPi package.
```bash
echo "sop-infra" >> local_requirements.txt
```
Add it to you `configuration.py`

```bash
sed -i "/PLUGINS = \[/a\    'sop_infra'," "netbox/netbox/configuration.py"
```
or with Python in netbox/netbox/configuration.py
```python
PLUGINS = [
    ...
    'sop-infra',
]
```
And upgrade NetBox
```bash
sudo bash upgrade.sh
```

## Customization
The following options are available:
- `display`
  - **Type**: dict {panel:position}
  - **Panels choices**: ['meraki', 'classification', 'sizing']
  - **Positions choices**: ['left_page', 'right_page']
  - **Description**: Chose what panel and where it should be displayed on dcim:site

Plugin config exemple in netbox/netbox/configuration.py
```python
PLUGINS_CONFIG = {
    'sop_infra': {
        'display': {
            'meraki':'left_page',
            'classification':'left_page',
            'sizing':'right_page'
        }
    }
}
```

With this exemple configuration,
meraki and classification panels will be displayed on the left
and sizing on the right of the Site detail page.

