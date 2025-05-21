<h1 align="center">
    NetBox - SOP-Infra plugin<br>
</h1>
<p align="center">
    <a href="https://github.com/netbox-community/netbox">NetBox</a> plugin to manage infrastructure informations of each site.
</p>

---

## 🚀 Features

- [**Sizing**](/docs/features/sizing.md)
- [**Search**](/docs/features/search.md)

---

## 📦 Installation

### Prerequisites

Ensure you have the following requirements:

- NetBox 4.1.0+
- Python 3.x

### Installation Steps

1. **Add Requirements**

   ```bash
   # add SOP-Infra plugin
   echo "sop-infra" >> local_requirements.txt
   ```

2. **Configure NetBox**

Edit `netbox/netbox/configuration.py` to include the plugin:

```python
PLUGINS = [
    # ... other plugins
    'sop_infra',
]
```

3. **Customization**
   The following options are available:

- `display`

  - **Type**: dict {panel:position}
  - **Panels choices**: ['meraki', 'classification', 'sizing']
  - **Positions choices**: ['left_page', 'right_page']
  - **Description**: Chose what panel and where it should be displayed on the Site.

> [!NOTE]
> Panels will be displayed on the site detail page..

- `prisma`
  - **client_id**:'string'
  - **client_scret**:'string'
  - **tsg_id**:'string'

Plugin config example in `netbox/netbox/netbox/configuration.py`

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

With this configuration, `Meraki` and `Classification` panels will be displayed on the `left` and `Sizing` on the `right` of the `Site detail` page.

4. **Upgrade NetBox**

   ```bash
   sudo ./upgrade.sh
   ```

## 📋 Models

The SOP-Infra plugin provides four core models:

- [**Sop Infra**](/docs/models/sop-infra.md)
- [**Prisma Endpoint**](/docs/models/prisma-endpoint.md)
- [**Prisma Access Location**](/docs/models/prisma-access-location.md)
- [**Prisma Computed Access Location**](/docs/models/prisma-computed-access-location.md)

---

## 🛠️ Development

- [**Contribute**](/docs/development/contribute.md)
- [**Unit-Tests**](/docs/development/unit-test.md)
- [**Deploy**](/docs/development/deploy.md)
