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
- `panels`
  - **Type**: List
  - **Choices**: ['meraki', 'classification', 'sizing']
  - **Description**: Chose what panel you want to display on dcim:site
- `display_default`
  - **Type**: String
  - **Choices**: ['left_page', 'right_page',...]
  - **Description**: Chose where all panels should be displayed by default.
- `display_custom`
  - **Type**: Dict
  - **Choices**: {'panel':'display'}
  - **Description**: Chose where specific panel should be displayed
  - **Override**: overrides `display_default`.

Plugin config exemple in netbox/netbox/configuration.py
```python
PLUGINS_CONFIG = {
    'sop_infra': {
        'panels': ['meraki', 'classification', 'sizing'],
        'display_default': 'left_page',
        'display_custom': {'sizing':'right_page'}
    }
}
```

With this exemple configuration,
meraki and classification panels will be displayed on the left
and sizing on the right of the Site detail page.

