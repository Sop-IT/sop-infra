<h1 align="center">
    Contribute<br>
</h1>

---

## Clean NetBox Installation (dev)

Install a clean NetBox version:

Follow [**NetBox**](https://github.com/netbox-community/netbox) official installation documentation.

Enable developer features and add the plugin in `netbox/netbox/netbox/configuration.py`

```bash
cat << eof > netbox/netbox/netbox/configuration.py
PLUGINS = [
    "sop_infra",
]
DEBUG = True
DEVELOPER = True
eof
```

---

## Plugin Installation (dev)

Clone the plugin repository:

```bash
git clone https://github.com/Sop-IT/sop-infra.git
```

Move the plugin in NetBox application root:

> [!TIP]
> Application root is the `netbox/` folder with `dcim/` `ipam/`...

```bash
cd sop-infra
mv sop_infra /path/to/netbox/netbox
```

Upgrade NetBox

```bash
cd /path/to/netbox
sudo bash upgrade.sh
```

---

## Add a new feature (dev)

Run a local Django server:

```bash
source venv/bin/activate
python3 netbox/manage.py runserver --insecure
```

Each time you make a change, Django reload the server.<br>
Do not forget to test your feature and to run unit-test to make sure you don't break any previous features. Refer to [**unit-test**](./unit-test.md).<br>
In order to deploy a new version of the plugin, refer to [**deploy**](./deploy.md).

---
