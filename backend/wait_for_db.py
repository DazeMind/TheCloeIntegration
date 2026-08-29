"""
Espera a que SQL Server acepte conexiones antes de correr migrate/runserver.

A diferencia de reintentar `manage.py migrate` en un bucle, esto SOLO reintenta
por fallos de conexion a la base de datos. Cualquier otro error (import, config,
etc.) se propaga de inmediato en lugar de disfrazarse de "esperando la BD".

Uso: python wait_for_db.py [intentos] [segundos_entre_intentos]
"""

import os
import sys
import time

import django
from django.db import connections
from django.db.utils import OperationalError, InterfaceError

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")


def main() -> int:
    attempts = int(sys.argv[1]) if len(sys.argv) > 1 else 20
    delay = float(sys.argv[2]) if len(sys.argv) > 2 else 3.0

    django.setup()
    conn = connections["default"]
    db = conn.settings_dict
    target = f"{db.get('HOST')}:{db.get('PORT')}/{db.get('NAME')} (user={db.get('USER')})"
    print(f"[wait_for_db] Conectando a {target}", flush=True)

    last_error = None
    for i in range(1, attempts + 1):
        try:
            conn.ensure_connection()
        except (OperationalError, InterfaceError) as exc:
            last_error = exc
            print(f"[wait_for_db] Intento {i}/{attempts} fallo: {exc}", flush=True)
            conn.close_if_unusable_or_obsolete()
            time.sleep(delay)
        else:
            print("[wait_for_db] Conexion establecida.", flush=True)
            return 0

    print(f"[wait_for_db] No se pudo conectar tras {attempts} intentos.", flush=True)
    print(f"[wait_for_db] Ultimo error: {last_error}", flush=True)
    print(
        "[wait_for_db] Revisa en el host: TCP/IP habilitado en SQL Server, "
        "puerto 1433 abierto en el firewall, autenticacion mixta (SQL login) "
        "y que el usuario tenga acceso a la base de datos.",
        flush=True,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
