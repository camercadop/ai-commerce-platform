# storage

Defines the abstract object storage port. Concrete implementations live in the domain
modules that require them (e.g. `app/media/`). Domain code must never depend on a
concrete storage provider directly (ADR-004).

## Package layout

```
storage/
├── __init__.py     # Package entry point
├── exceptions.py   # Storage-specific exceptions
└── port.py         # Object storage abstraction layer
```

## Public API

| Symbol | Description |
| --- | --- |
| `ObjectStorage` | Abstract port with `put`, `get`, `delete`, and `exists` operations |
| `ObjectNotFound` | Raised by `get()` when no object exists at the given key |

### ObjectStorage interface

| Method | Description |
| --- | --- |
| `put(key, data, content_type)` | Stores raw bytes at the given key; overwrites if the key exists |
| `get(key)` | Returns the raw bytes stored at the key; raises `ObjectNotFound` if absent |
| `delete(key)` | Deletes the object at the key; no-op if the key does not exist |
| `exists(key)` | Returns `True` if an object exists at the key, `False` otherwise |

Keys are opaque path strings. Callers are responsible for namespacing conventions
(e.g. `products/<id>/image.jpg`). No provider-specific SDK or data format may appear
in domain code.
