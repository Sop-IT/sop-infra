<h1 align="center">
    Sop Infra<br>
</h1>

## Overview

The `SopInfra` model represents an infrastructure associated with a site. It ensures integrity and auto-computing through various constraints and validations.

---

## Attributes

### Site

- **Field:** `site`
- **Type:** `ForeignKey` to NetBox `Site` model
- **Details:**
  - Indicates the site where the `SopInfra` belongs
  - Cannot be `null`
  - Deletion of the related `Site` cascade

### System Infrastructure

- **Field:** `site_infra_sysinfra`
- **Type:** `CharField` with choices
- **Details:**
  - Simple BOX server
  - Super Box
  - Full cluster

### Industrial

- **Field:** `site_type_indus`
- **Type:** `CharField` with choices
- **Details:**
  - WRK - Workshop
  - FAC - Factory

### Criticity Stars

- **Field:** `criticity_stars`
- **Type:** `CharField`
- **Details:**
  - Criticality ratings
  - Calculated

### Phone Critical?

- **Field:** `site_phone_critical`
- **Type:** `CharField` with booleans
- **Details:**
  - True
  - False
  - Unknown

### R&D?

- **Field:** `site_type_red`
- **Type:** `CharField` with booleans
- **Details:**
  - True
  - False
  - Unknown

### VIP?

- **Field:** `site_type_vip`
- **Type:** `CharField` with booleans
- **Details:**
  - True
  - False
  - Unknown

### WMS?

- **Field:** `site_type_wms`
- **Type:** `CharField` with booleans
- **Details:**
  - True
  - False
  - Unknown

### EST. cumulative users

- **Field:** `est_cumulative_users`
- **Type:** `PositiveBigInteger`
- **Details:**
  - Estimated cumulative users

### AD Direct Users

- **Field:** `ad_direct_users`
- **Type:** `PositiveBigInteger`
- **Details:**
  - Active Directory direct users

### WAN Computed Users

- **Field:** `wan_computed_users`
- **Type:** `PositiveBigInteger`
- **Details:**
  - Total computed wan users
  - Calculated field

### WAN Reco. BW

- **Field:** `wan_reco_bw`
- **Type:** `PositiveBigInteger`
- **Details:**
  - Recommended bandwidth (Mbps)
  - Calculated field

### Site MX Model

- **Field:** `site_mx_model`
- **Type:** `CharField`
- **Details:**
  - Recommended MX Model
  - Calculated field

### Site User Count

- **Field:** `site_user_count`
- **Type:** `PositiveBigInteger`
- **Details:**
  - Site user slice
  - Calculated field

### SDWANHA

- **Field:** `sdwanha`
- **Type:** `CharField` with choices
- **Details:**
  - HA(S)/NHA Target
  - Calculated field

### HUB order setting

- **Field:** `hub_order_setting`
- **Type:** `CharField` with choices
- **Details:**
  - EQX-NET-COX-DDC
  - COX-DDC-EQX-NET
  - NET-EQX-COX-DDC
  - DDC-COX-EQX-NET

### HUB default route setting

- **Field:** `hub_default_route_setting`
- **Type:** `CharField` with booleans
- **Details:**
  - True
  - False
  - Unknown

### SDWAN1 BW

- **Field:** `sdwan1_bw`
- **Type:** `CharField`
- **Details:**
  - SDWAN > WAN1 Bandwidth (real link bandwidth)

### SDWAN2 BW

- **Field:** `sdwan2_bw`
- **Type:** `CharField`
- **Details:**
  - SDWAN > WAN2 Bandwidth (real link bandwidth)

### Master Location

- **Field:** `site_sdwan_master_location`
- **Type:** `ForeignKey` to NetBox `Location` model
- **Details:**
  - Materialize the location of the MASTER site

### Master Site

- **Field:** `master_site`
- **Type:** `ForeignKey` to NetBox `Site` model
- **Details:**
  - Materialize the site of the MASTER site

### Migration SDWAN

- **Field:** `migration_sdwan`
- **Type:** `DateField` 
- **Details:**
  - SDWAN > Site migration date to SDWAN

### Monitor in starting

- **Field:** `monitor_in_starting`
- **Type:** `BooleanField` 
- **Details:**
  - Should centreon monitor this site when its status is "starting"

### Endpoint

### Enabled

### Valid

---
