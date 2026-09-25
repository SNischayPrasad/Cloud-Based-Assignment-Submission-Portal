"""
Cloud abstraction layer.

The rest of the application talks to these three services only:

* database_service - SQLAlchemy engine/session (SQLite locally, managed PostgreSQL in the cloud)
* storage_service  - object storage (local folder locally, S3 / Supabase Storage / R2 / MinIO in the cloud)
* auth_service     - password hashing + JWT access tokens

Swapping a local component for a managed cloud service is a configuration
change (environment variables), not a code change.
"""
