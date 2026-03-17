"""
Harmoni — ZKTeco Biometric Device Integration (Facade).

High-level interface for interacting with ZKTeco biometric devices
via TCP/UDP using the pyzk library.

This module provides a standalone ``ZKTecoService`` class that can be used
without a Django ``RelojBiometrico`` model instance — useful for scripting,
management commands, and ad-hoc connections.

For the model-backed integration used by views and Celery tasks, see
``asistencia.services.zk_service.ZKService``.

Requisito: pip install pyzk
"""
from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Any

from django.utils import timezone

logger = logging.getLogger('harmoni.zkteco')


# ── Mapeo de códigos punch ZKTeco → Harmoni ────────────────────────────────

_PUNCH_MAP: dict[int, str] = {
    0: 'ENTRADA',
    1: 'SALIDA',
    2: 'DESCANSO_SALIDA',
    3: 'DESCANSO_REGRESO',
    4: 'HE_SALIDA',
    5: 'OTRO',
    255: 'OTRO',
}


def _map_punch(punch: int) -> str:
    """Traduce código punch ZKTeco a tipo_marcacion de Harmoni."""
    return _PUNCH_MAP.get(punch, 'OTRO')


class ZKTecoService:
    """
    Interface with ZKTeco devices via TCP (pyzk library).

    This is a stateful service — call ``connect()`` first, then perform
    operations, and finally call ``disconnect()``.  It can also be used as
    a context manager::

        svc = ZKTecoService()
        with svc:
            svc.connect('192.168.1.100')
            users = svc.get_users()

    For one-shot operations use ``test_connection()`` which manages the
    connection lifecycle internally.
    """

    def __init__(self):
        self._conn = None
        self._zk = None

    # ── Context manager ──────────────────────────────────────────────────

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()
        return False

    # ── Connection management ────────────────────────────────────────────

    def connect(self, ip: str, port: int = 4370, timeout: int = 10) -> bool:
        """
        Establish a TCP/UDP connection with a ZKTeco device.

        Args:
            ip:      IPv4 address of the device.
            port:    ZK protocol port (default 4370).
            timeout: Connection timeout in seconds.

        Returns:
            True if the connection was established successfully.

        Raises:
            ImportError: If pyzk is not installed.
            ConnectionError: If the device is unreachable or refused connection.
        """
        try:
            from zk import ZK
        except ImportError:
            raise ImportError(
                'pyzk no está instalado. Ejecuta: pip install pyzk'
            )

        self.disconnect()  # close any previous connection

        self._zk = ZK(
            ip,
            port=port,
            timeout=timeout,
            ommit_ping=False,
            verbose=False,
        )

        try:
            self._conn = self._zk.connect()
            logger.info('ZKTeco connected: %s:%d', ip, port)
            return True
        except Exception as exc:
            logger.warning('ZKTeco connect failed %s:%d — %s', ip, port, exc)
            self._conn = None
            raise ConnectionError(
                f'No se pudo conectar al dispositivo {ip}:{port} — {exc}'
            ) from exc

    def disconnect(self):
        """Safely close the current connection."""
        if self._conn:
            try:
                self._conn.disconnect()
            except Exception:
                pass
            finally:
                self._conn = None
                self._zk = None

    @property
    def is_connected(self) -> bool:
        return self._conn is not None

    # ── Device info ──────────────────────────────────────────────────────

    def test_connection(self, ip: str, port: int = 4370) -> dict:
        """
        Test connectivity and retrieve device information.

        Does NOT require a prior ``connect()`` call — manages the lifecycle
        internally.

        Returns:
            {
                'ok': bool,
                'detail': str,
                'info': {
                    'serial': str,
                    'firmware': str,
                    'platform': str,
                    'device_time': str,
                    'user_count': int,
                    'attendance_count': int,
                },
            }
        """
        try:
            self.connect(ip, port)
        except (ImportError, ConnectionError) as exc:
            return {'ok': False, 'detail': str(exc), 'info': {}}

        try:
            serial = self._conn.get_serialnumber() or ''
            firmware = ''
            platform = ''
            device_time = ''

            try:
                firmware = str(self._conn.get_firmware_version() or '')
            except Exception:
                pass
            try:
                platform = str(self._conn.get_platform() or '')
            except Exception:
                pass
            try:
                device_time = str(self._conn.get_time())
            except Exception:
                pass

            # Count records
            user_count = 0
            att_count = 0
            try:
                users = self._conn.get_users() or []
                user_count = len(users)
            except Exception:
                pass
            try:
                atts = self._conn.get_attendance() or []
                att_count = len(atts)
            except Exception:
                pass

            info = {
                'serial': serial,
                'firmware': firmware,
                'platform': platform,
                'device_time': device_time,
                'user_count': user_count,
                'attendance_count': att_count,
            }
            return {
                'ok': True,
                'detail': f'Conectado. Serie: {serial or "N/D"}, '
                          f'{user_count} usuarios, {att_count} marcaciones',
                'info': info,
            }
        except Exception as exc:
            logger.warning('ZKTeco test_connection error %s:%d — %s', ip, port, exc)
            return {
                'ok': False,
                'detail': f'Error al consultar dispositivo: {exc}',
                'info': {},
            }
        finally:
            self.disconnect()

    # ── Attendance ───────────────────────────────────────────────────────

    def get_attendance(self, from_date: date | None = None) -> list[dict]:
        """
        Download attendance records from the connected device.

        Args:
            from_date: If provided, only return records on or after this date.

        Returns:
            List of dicts:
            [
                {
                    'user_id': str,
                    'timestamp': datetime,
                    'punch': int,
                    'tipo': str,   # Harmoni type name
                },
                ...
            ]

        Raises:
            RuntimeError: If not connected.
        """
        if not self._conn:
            raise RuntimeError('No hay conexión activa. Llama connect() primero.')

        try:
            raw_records = self._conn.get_attendance() or []
        except Exception as exc:
            logger.error('ZKTeco get_attendance error: %s', exc)
            raise RuntimeError(f'Error al leer marcaciones: {exc}') from exc

        result: list[dict] = []
        for att in raw_records:
            uid = str(getattr(att, 'user_id', '') or '').strip()
            if not uid:
                continue

            ts = getattr(att, 'timestamp', None)
            if ts is None:
                continue
            if not isinstance(ts, datetime):
                try:
                    ts = datetime.combine(date.today(), ts)
                except Exception:
                    continue

            # Filter by from_date
            if from_date and ts.date() < from_date:
                continue

            punch = int(getattr(att, 'punch', 0) or 0)

            result.append({
                'user_id': uid,
                'timestamp': ts,
                'punch': punch,
                'tipo': _map_punch(punch),
            })

        return result

    def clear_attendance(self) -> bool:
        """
        Clear all attendance records from the device memory.

        WARNING: This permanently deletes records from the device.
        Make sure to download them first with ``get_attendance()`` or
        ``pull_attendance()``.

        Returns:
            True if records were cleared successfully.

        Raises:
            RuntimeError: If not connected.
        """
        if not self._conn:
            raise RuntimeError('No hay conexión activa. Llama connect() primero.')

        try:
            self._conn.clear_attendance()
            logger.info('ZKTeco attendance cleared successfully')
            return True
        except Exception as exc:
            logger.error('ZKTeco clear_attendance error: %s', exc)
            raise RuntimeError(f'Error al limpiar marcaciones: {exc}') from exc

    # ── Users ────────────────────────────────────────────────────────────

    def get_users(self) -> list[dict]:
        """
        Get list of users enrolled on the connected device.

        Returns:
            List of dicts:
            [
                {
                    'uid': int,
                    'user_id': str,
                    'name': str,
                    'privilege': int,
                    'password': str,
                    'card': str,
                },
                ...
            ]

        Raises:
            RuntimeError: If not connected.
        """
        if not self._conn:
            raise RuntimeError('No hay conexión activa. Llama connect() primero.')

        try:
            users = self._conn.get_users() or []
            return [
                {
                    'uid': u.uid,
                    'user_id': u.user_id,
                    'name': u.name,
                    'privilege': u.privilege,
                    'password': u.password,
                    'card': getattr(u, 'card', '') or '',
                }
                for u in users
            ]
        except Exception as exc:
            logger.error('ZKTeco get_users error: %s', exc)
            raise RuntimeError(f'Error al leer usuarios: {exc}') from exc

    def sync_users(self, employees: list[dict]) -> dict:
        """
        Upload/sync employee records to the device.

        For each employee dict, creates or updates the user on the device
        using the DNI as user_id.

        Args:
            employees: List of dicts with keys:
                - 'user_id' (str):  DNI or badge number (required)
                - 'name' (str):     Employee name (max 24 chars on most devices)
                - 'privilege' (int): 0=user, 2=admin (default 0)
                - 'password' (str): Optional PIN
                - 'card' (str):     Optional card number

        Returns:
            {
                'ok': bool,
                'uploaded': int,    # successfully uploaded
                'skipped': int,     # already existed (same user_id)
                'errors': int,      # failed to upload
                'details': list,    # error details
            }

        Raises:
            RuntimeError: If not connected.
        """
        if not self._conn:
            raise RuntimeError('No hay conexión activa. Llama connect() primero.')

        # Get existing users to detect already-enrolled ones
        try:
            existing = self._conn.get_users() or []
            existing_ids = {u.user_id for u in existing}
        except Exception:
            existing_ids = set()

        uploaded = skipped = errors = 0
        details: list[str] = []

        for emp in employees:
            user_id = str(emp.get('user_id', '')).strip()
            if not user_id:
                errors += 1
                details.append('Empleado sin user_id')
                continue

            if user_id in existing_ids:
                skipped += 1
                continue

            name = str(emp.get('name', ''))[:24]  # ZKTeco name limit
            privilege = int(emp.get('privilege', 0))
            password = str(emp.get('password', ''))
            card = str(emp.get('card', ''))

            try:
                self._conn.set_user(
                    uid=0,  # auto-assign
                    name=name,
                    privilege=privilege,
                    password=password,
                    user_id=user_id,
                    card=int(card) if card.isdigit() else 0,
                )
                uploaded += 1
                existing_ids.add(user_id)
            except Exception as exc:
                errors += 1
                details.append(f'{user_id}: {exc}')
                logger.warning('ZKTeco set_user error for %s: %s', user_id, exc)

        logger.info(
            'ZKTeco sync_users: uploaded=%d skipped=%d errors=%d',
            uploaded, skipped, errors,
        )

        return {
            'ok': errors == 0,
            'uploaded': uploaded,
            'skipped': skipped,
            'errors': errors,
            'details': details,
        }


# ── Convenience functions for model-backed operations ────────────────────

def sync_device_attendance(reloj, user=None) -> dict:
    """
    Download attendance from a ``RelojBiometrico`` and save to
    ``MarcacionBiometrica``, deduplicating by unique_together.

    This is a thin wrapper that delegates to the standalone ``ZKTecoService``
    but handles model persistence (saving to Django ORM).

    Args:
        reloj: ``RelojBiometrico`` model instance.
        user:  Django User for audit trail (optional).

    Returns:
        Same dict format as ``ZKService.pull_attendance()``.
    """
    from asistencia.models import MarcacionBiometrica, RelojBiometrico
    from personal.models import Personal

    svc = ZKTecoService()

    try:
        svc.connect(reloj.ip, port=reloj.puerto, timeout=reloj.timeout)
    except (ImportError, ConnectionError) as exc:
        RelojBiometrico.objects.filter(pk=reloj.pk).update(
            estado_conexion='ERROR',
            ultima_verificacion=timezone.now(),
        )
        return {
            'ok': False, 'total': 0, 'nuevos': 0,
            'omitidos': 0, 'sin_match': 0, 'error': str(exc),
        }

    try:
        records = svc.get_attendance()
    except RuntimeError as exc:
        RelojBiometrico.objects.filter(pk=reloj.pk).update(
            estado_conexion='ERROR',
        )
        return {
            'ok': False, 'total': 0, 'nuevos': 0,
            'omitidos': 0, 'sin_match': 0, 'error': str(exc),
        }
    finally:
        svc.disconnect()

    total = len(records)
    if total == 0:
        RelojBiometrico.objects.filter(pk=reloj.pk).update(
            ultima_sincronizacion=timezone.now(),
            estado_conexion='CONECTADO',
        )
        return {
            'ok': True, 'total': 0, 'nuevos': 0,
            'omitidos': 0, 'sin_match': 0, 'error': '',
        }

    # Build DNI → Personal map
    user_ids = {r['user_id'] for r in records}
    personal_map: dict[str, Any] = {}
    if reloj.campo_id_empleado == 'USER_ID' and user_ids:
        qs = Personal.objects.filter(nro_doc__in=user_ids).only('id', 'nro_doc')
        personal_map = {p.nro_doc: p for p in qs}

    nuevos = omitidos = sin_match = 0

    for rec in records:
        uid = rec['user_id']
        personal_obj = personal_map.get(uid)
        if not personal_obj:
            sin_match += 1

        _, created = MarcacionBiometrica.objects.get_or_create(
            reloj=reloj,
            user_id_dispositivo=uid,
            timestamp=rec['timestamp'],
            defaults={
                'personal': personal_obj,
                'tipo_marcacion': rec['tipo'],
                'punch_raw': rec['punch'],
            },
        )
        if created:
            nuevos += 1
        else:
            omitidos += 1

    RelojBiometrico.objects.filter(pk=reloj.pk).update(
        ultima_sincronizacion=timezone.now(),
        estado_conexion='CONECTADO',
    )

    logger.info(
        'ZKTeco device sync [%s]: total=%d nuevos=%d omitidos=%d sin_match=%d',
        reloj.nombre, total, nuevos, omitidos, sin_match,
    )

    return {
        'ok': True,
        'total': total,
        'nuevos': nuevos,
        'omitidos': omitidos,
        'sin_match': sin_match,
        'error': '',
    }
