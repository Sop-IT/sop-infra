<h1 align="center">
    Unit-Test<br>
</h1>

## Overview

The plugin contains django unit-test in order to check its proper functioning as modifications are made.

---

## Run Tests

1. **Add Requirements**

```bash
echo "django-test-without-migrations" >> local_requirements.txt
```

2. **Run tests**

```bash
python3 netbox/manage.py test -n sop_infra.tests
```

---

## How do I ?

### Update NetBox version in GitAction

SOP-Infra plugin contains a GitAction that `run` unit-tests on `main` branch `push`.<br>
Current `NetBox version` is **v4.1.1**. To update it, go to [**test.yml**](/.github/workflows/test.yml) and modify **NETBOX_VERSION** in the `env` variable:<br>

```yaml
env:
  NETBOX_VERSION: v4.1.1
```

> [!NOTE]
> NETBOX_VERSION must correspond to a valid NetBox branch.

### Write Unit-Tests

1. **Create a new test file**

To write additional unit-tests, you will need to create a `python` in the plugin [**tests**](/sop_infra/tests) folder. The file name **must** begin with `test_` and end with `.py`.
For example:

```bash
mkdir -p tests
touch tests/test_validations.py
```

2. **Import your dependencies**

```python
#mandatory NetBox TestCase class
from utilities.testing import TestCase

#import the class/functions you wan to test
from dcim.models import Site, Location
from sop_infra.models import SopInfra

```

3. **Create your TestCase class**

```python
# the function must inherits TestCase class
class SopInfraFeaturesTestCase(TestCase):

    @classmethod
    def setUpTestData(cls):
        """method to perform initializations related to the entire class"""
        # lets initialize test Site
        cls.site1 = Site.objects.create(name="site1", slug="site-1", status="active")
        cls.site2 = Site.objects.create(name="site2", slug="site-2", status="inactive")
        cls.site3 = Site.objects.create(name="site2", slug="site-2", status="starting")
        cls.loc1 = Location.objects.create(name="loca1", slug="loca-1", status="active", site=cls.site1)
```

4. **Create your testing methods**

Each method must begin with `test_`. You can also add a method description that will print on error.

```python
def test_valid_master_site(self):
    """Here is the method description"""
    # entry should be valid
    infra = SopInfra.objects.create(site=self.site1, master_site=self.site2)
    infra.full_clean()
    infra.save()

    # so we check if NetBox successfully created 1 SopInfra objects
    self.assertEqual(SopInfra.objects.all().count(), 1)
```

TestCase also provides `exceptions raises`. Import the following django packages:

```python
# import the right packages
from django.db import IntegrityError, transaction
from django.core.exceptions import ValidationError
```

And in `SopInfraFeaturesTestCase` class, add the following method:

```python

def test_create_invalid_infra(self):
    """Test that invalid DID raises correct exceptions"""
    # invalid: Master Site loop -> raise database constraint exception
    with transaction.atomic():
        with self.assertRaises(IntegrityError):
            infra = SopInfra.objects.create(site=self.site1)
            infra.master_site=self.site1
            infra.save()

    # invalid: Master Site != Master Location's site -> raise ValidationError
    with self.assertRaises(ValidationError):
        infra = SopInfra.objects.create(site=self.site2)
        infra.master_location = self.loc1
        infra.master_site = self.site3
        infra.full_clean()

```

5. **Test views and permissions**

NetBox TestCase class also provides _views-tests methods_. For example:

```python
def test_this_view_perm(self):
    """test your view without permissions"
    url:str = '/my/view/url'

    # NetBox TestCase method for GET response
    response = self.client.get(url)

    # assert HTTP response code is equal to 403
    self.assertHttpStatus(response, 403)

    # NetBox TestCase method to add a single permission
    self.add_permissions('my_view_url_permissions')
    self.assertHttpStatus(response, 200)

```
