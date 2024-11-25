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

- `prisma`
  - **access_token**:'string'
  - **client_id**:'string'
  - **client_scret**:'string'
  - **tsg_id**:'string'
  - **payload_url**:'string'

Plugin config exemple in netbox/netbox/configuration.py

```python
PLUGINS_CONFIG = {
    'sop_infra': {
        'display': {
            'meraki':'left_page',
            'classification':'left_page',
            'sizing':'right_page'
        },
        'prisma': {
            'client_id':''
            'client_scret':''
            'tsg_id':''
        },
    }
}
```

With this exemple configuration,
meraki and classification panels will be displayed on the left
and sizing on the right of the Site detail page.

## Development

The repository will automatically execute unit-tests on every main push.

Tests will be executed on NetBox v4.1.1
To change this version, edit [`test.yml`](https://github.com/Sop-IT/sop-infra/blob/main/.github/workflows/test.yml)
`NETBOX_VERSION` variable.

```yml
env:
  NETBOX_VERSION: v4.1.1
```

Django unit-tests must be in [`tests`](https://github.com/Sop-IT/sop-infra/tree/main/sop_infra/tests) folder.
