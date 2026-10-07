# Storage & Cloud Object Disks

Craft Engine provides a unified, expressive filesystem abstraction for local disks, public assets, and S3-compatible cloud storage (AWS S3, MinIO, Cloudflare R2, Google Cloud Storage).

## 🚀 Basic Usage

```python
from craft.facades import Storage

# 1. Store contents
Storage.put("documents/report.pdf", pdf_bytes)

# 2. Check existence & read
if Storage.exists("documents/report.pdf"):
    content = Storage.get("documents/report.pdf")
    size = Storage.size("documents/report.pdf")
    mime = Storage.mime_type("documents/report.pdf")

# 3. Public or S3 URL
url = Storage.url("documents/report.pdf")

# 4. Signed Temporary URL (for private files)
temp_url = Storage.temporary_url("documents/report.pdf", minutes=15)

# 5. Delete file
Storage.delete("documents/report.pdf")
```

---

## ☁️ Multi-Disk Switching (`local`, `public`, `s3`)

Configured in `config/storage.py`:

```python
# Upload directly to S3 disk
Storage.disk("s3").put("backups/database.sql", backup_content)

# Read from public disk
avatar_url = Storage.disk("public").url("avatars/user_1.jpg")
```

## Tenant-Scoped Disks

A disk with `"tenant_scoped": true` keeps each tenant's files under
`tenants/<tenant_id>/`. The path you pass is relative to the tenant's own
directory, so one tenant can never name another's file, and a call with no
tenant bound raises `TenantNotBoundError` instead of writing to a shared root:

```python
# config/storage.py
"tenant": {"driver": "local", "root": "storage/app", "tenant_scoped": True},

Storage.disk("tenant").put("contracts/2026.pdf", pdf)   # storage/app/tenants/<id>/contracts/2026.pdf
```

## Safe Paths

Every key is validated before it is used, by the local and S3 drivers alike: a
`..` segment, an absolute path, a `\0` byte or a `scheme://` is refused with a
`ValueError`, whether the key is written to disk or rendered into a URL. A
stored filename is therefore never a traversal, and neither is a link.

