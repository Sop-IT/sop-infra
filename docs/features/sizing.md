<h1 align="center">
    Sizing<br>
</h1>

## Overview

This features provides detailed sizing capabilities for SOP-Infra objects, based of the `Site` status and `Active Directory`.

---

## Sizing details

### WAN Computed Users

Computes `WAN Computed Users` according to `site's status`.<br>
Status:

- **Active, Decommissioning:** WAN is the `AD Direct Users`.
- **Candidate, Planned, Staging:** WAN is the `EST Cumulative Users`.
- **Starting:** WAN is the `AD Direct Users` unless `EST Cumulative Users` is bigger than Direct.

> [!NOTE]
> Slave Site wan users is added to Master Site wan users.

### MX and User Slice

Computes `MX` and `User Slice` according to `wan computed users`.

| WAN  | User Slice | MX    |
| ---- | ---------- | ----- |
| <10  | <10        | MX67  |
| <20  | 10<20      | MX67  |
| <50  | 20<50      | MX68  |
| <100 | 50<100     | MX85  |
| <200 | 100<200    | MX95  |
| <500 | 200<500    | MX95  |
| >500 | >500       | MX250 |

### Recommended Bandwidth

Computes `Recommended Bandwidth` according to `wan computed users`.
| WAN | Reco. BW |
| --- | -------- |
| >100 | `wan * 2.5` |
| >50 | `wan * 3` |
| >10 | `wan * 4` |
| <10 | `wan * 5` |

---
