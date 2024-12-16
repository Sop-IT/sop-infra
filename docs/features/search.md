<h1 align="center">
    Search<br>
</h1>

## Global search

SOP-Infra plugin is compatible with NetBox global search engine. It allows you to search for objects in the exact format as stored in the database, while also supporting indexing for quick lookups.

---

## Filters

Each model in the SOP-Infra plugin provides its own set of filters on the `list` view page. The filters enable you to retrieve specific objects abused on various criteria, tailored to the model attributes.

### Location Filters

SOP-Infra model has a set of location-based filters, allowing you to narrow down objects by geographical or organizational context. The supported filters include:

- **Region:** Use the query parameter `?region_id=` to filter objects by their associated Region ID.
- **Site Group:** Use the query parameter `?group_id=` to filter objects by their associated Site Group ID.
- **Site:** Use the query parameters `?site_id=` to filter objects associated with specific Site ID.

---
