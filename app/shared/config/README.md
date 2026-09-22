# config

Provides the base settings class for all domain configuration. Every domain and shared
package that needs environment-driven configuration must subclass `AppSettings` rather
than reading environment variables directly.

## Package layout

```
config/
├── __init__.py     # Package entry point
└── base.py         # Base settings class
```

## Public API

| Symbol | Description |
| --- | --- |
| `AppSettings` | Pydantic `BaseSettings` subclass; reads from `.env` and environment variables |

## Behavior

- Reads from a `.env` file and the process environment. Environment variables take
  precedence over `.env` values.
- Key lookup is case-insensitive.
- Extra keys present in the environment are silently ignored.
- A missing required field raises a `ValidationError` at import time, causing the
  application to fail before serving any traffic (ADR-015).

## Defining domain settings

Declare each configuration key as a typed field. Required keys have no default;
optional keys declare one:

```python
from app.shared.config import AppSettings


class CatalogSettings(AppSettings):
    database_base_url: str
    kafka_bootstrap_servers: str
    feature_flag_enabled: bool = False
```
