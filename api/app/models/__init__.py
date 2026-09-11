"""
Modelos de Zentra+.

Todo lo que sea una tabla se reexporta aqui: es lo que leen alembic/env.py para
detectar el esquema y los tests para crear las tablas. Un modelo que no aparezca
en este archivo no existe para las migraciones.
"""

from app.models.base import IdUUID, Timestamps, ahora_utc

__all__ = ["IdUUID", "Timestamps", "ahora_utc"]
