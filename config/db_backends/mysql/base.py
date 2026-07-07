"""Custom MySQL backend that pins ``has_native_uuid_field`` to ``False``.

Django auto-detects native UUID column support from the connected server's
version: ``django.db.backends.mysql.features.DatabaseFeatures.has_native_uuid_field``
is ``True`` whenever the server is MariaDB >= 10.7 (MariaDB added a real
native ``UUID`` column type in 10.7). When that flag is ``True``,
``UUIDField.get_db_prep_value()`` skips its usual ``.hex`` conversion and
passes the raw ``uuid.UUID`` object straight through, assuming the target
column is a native UUID type that can store it directly.

Every ``UUIDField`` column in this project (``StatisticsRequest.public_id``,
``TikTokWatchHistoryStatistics.public_id``, ``MDMProfile.public_id``, etc.)
was created as a plain ``char(32)`` column.
A DB-side MariaDB upgrade (observed on 07.07.2026 - v10.11.18) seems to have
flipped the flag on with no application code change at all, and the driver's
fallback serialization of a raw ``UUID`` object (its 36-character dashed
``str()`` form) can never match the stored 32-character hex values - every
``WHERE public_id = ...`` lookup silently stops matching, and every new
write silently gets truncated into invalid hex.

Forcing the flag back to ``False`` restores the ``.hex``-based read/write
behaviour the schema was actually built for, regardless of the server's
MariaDB version. This only changes how Django's ORM serializes/compares
``UUIDField`` values - it does not touch the database itself.
"""

from django.db.backends.mysql.base import DatabaseWrapper as MySQLDatabaseWrapper
from django.db.backends.mysql.features import (
    DatabaseFeatures as MySQLDatabaseFeatures,
)


class DatabaseFeatures(MySQLDatabaseFeatures):
    has_native_uuid_field = False


class DatabaseWrapper(MySQLDatabaseWrapper):
    features_class = DatabaseFeatures
