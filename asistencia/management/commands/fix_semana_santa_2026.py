"""
Management command: fix_semana_santa_2026
==========================================
Corrige el tratamiento de Jueves y Viernes Santo 2026 en la asistencia.

Acciones:
  1. Carga Jueves Santo (02-abr) y Viernes Santo (03-abr) en FeriadoCalendario.
  2. Registra compensaciones en CompensacionFeriado:
       - 02-abr → 04-abr  (STAFF)
       - 03-abr → 05-abr  (FORANEO 4h)
       - 03-abr → 12-abr  (FORANEO 4h)
  3. Recalcula HE en RegistroTareo para quienes TRABAJARON esos días:
       - es_feriado = True
       - Todos las horas efectivas → he_100 (HE 100%)
       - horas_normales = 0, he_25 = 0, he_35 = 0
  4. Crea registros DS (descanso compensatorio) para quienes tomaron
     el día libre como compensación y NO aparecen en esos días.
  5. Recalcula BancoHoras de los STAFF afectados (abril 2026).

Uso:
    python manage.py fix_semana_santa_2026
    python manage.py fix_semana_santa_2026 --dry-run
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction


IMPORTACION_ASISTENCIA_ID = 20  # La importacion creada por sync_datos_abril_2026

# Jornadas efectivas por condicion/dia (igual que en sync command)
JORNADA = {
    'LOCAL':   {0: 8.5, 1: 8.5, 2: 8.5, 3: 8.5, 4: 8.5, 5: 5.5, 6: 0.0},
    'FORANEO': {0: 11.0, 1: 11.0, 2: 11.0, 3: 11.0, 4: 11.0, 5: 11.0, 6: 4.0},
    'LIMA':    {0: 8.5, 1: 8.5, 2: 8.5, 3: 8.5, 4: 8.5, 5: 5.5, 6: 0.0},
}


def _jornada(condicion: str, fecha: date) -> float:
    cond = condicion or 'LOCAL'
    if 'FORANEO' in cond or 'FORÁNEO' in cond:
        cond = 'FORANEO'
    elif cond == 'LIMA':
        cond = 'LIMA'
    else:
        cond = 'LOCAL'
    return JORNADA.get(cond, JORNADA['LOCAL'])[fecha.weekday()]


class Command(BaseCommand):
    help = 'Corrige feriados Semana Santa 2026 y compensaciones en asistencia'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run', action='store_true',
            help='Muestra que cambiaria sin guardar nada'
        )

    def handle(self, *args, **options):
        self.dry = options['dry_run']
        if self.dry:
            self.stdout.write('=== DRY-RUN: no se guardara nada ===\n')

        with transaction.atomic():
            self._cargar_feriados()
            self._fix_he_feriado()
            self._crear_ds_compensacion()
            self._recalc_banco()

            if self.dry:
                self.stdout.write('\nDRY-RUN: revertiendo cambios...')
                transaction.set_rollback(True)

        self.stdout.write(self.style.SUCCESS('\nFeriados Semana Santa 2026 corregidos.'))

    # ------------------------------------------------------------------
    # 1. FERIADOS Y COMPENSACIONES
    # ------------------------------------------------------------------

    def _cargar_feriados(self):
        from asistencia.models import FeriadoCalendario, CompensacionFeriado

        self.stdout.write('\n[1/4] Cargando feriados y compensaciones...')

        feriados_data = [
            (date(2026, 4, 2), 'Jueves Santo', 'NACIONAL'),
            (date(2026, 4, 3), 'Viernes Santo', 'NACIONAL'),
        ]
        for fecha, nombre, tipo in feriados_data:
            obj, created = FeriadoCalendario.objects.get_or_create(
                fecha=fecha,
                defaults={'nombre': nombre, 'tipo': tipo, 'activo': True}
            )
            status = 'CREADO' if created else 'YA EXISTE'
            self.stdout.write(f'  {status}: {fecha} - {nombre}')

        # Compensaciones
        comp_data = [
            # (feriado,           compensada,        descripcion)
            (date(2026, 4, 2), date(2026, 4, 4), 'Jueves Santo → STAFF descansa 04-abr (Sab)'),
            (date(2026, 4, 3), date(2026, 4, 5), 'Viernes Santo → FORANEO descanso 4h 05-abr (Dom)'),
            (date(2026, 4, 3), date(2026, 4, 12), 'Viernes Santo → FORANEO descanso 4h 12-abr (Dom)'),
        ]
        for f_feriado, f_comp, desc in comp_data:
            obj, created = CompensacionFeriado.objects.get_or_create(
                fecha_feriado=f_feriado,
                fecha_compensada=f_comp,
                defaults={'descripcion': desc, 'activo': True}
            )
            status = 'CREADO' if created else 'YA EXISTE'
            self.stdout.write(f'  {status}: comp {f_feriado} -> {f_comp}')

    # ------------------------------------------------------------------
    # 2. RECALCULAR HE EN DIAS FERIADO
    # ------------------------------------------------------------------

    def _fix_he_feriado(self):
        from asistencia.models import RegistroTareo

        self.stdout.write('\n[2/4] Recalculando HE para trabajadores en dias feriado...')

        fechas_feriado = [date(2026, 4, 2), date(2026, 4, 3)]
        registros = RegistroTareo.objects.filter(
            importacion_id=IMPORTACION_ASISTENCIA_ID,
            fecha__in=fechas_feriado,
            codigo_dia='T',          # Solo quienes trabajaron (T = presencia)
            es_feriado=False,        # Aun no corregidos
        )

        corregidos = 0
        he_25_liberadas = Decimal('0')
        he_35_liberadas = Decimal('0')
        he_100_ganadas  = Decimal('0')

        bulk_updates = []
        for r in registros.select_for_update():
            he_25_liberadas += r.he_25
            he_35_liberadas += r.he_35
            he_100_ganadas  += r.horas_efectivas

            r.es_feriado    = True
            r.horas_normales = Decimal('0')
            r.he_25         = Decimal('0')
            r.he_35         = Decimal('0')
            r.he_100        = r.horas_efectivas
            bulk_updates.append(r)
            corregidos += 1

        if not self.dry and bulk_updates:
            RegistroTareo.objects.bulk_update(
                bulk_updates,
                ['es_feriado', 'horas_normales', 'he_25', 'he_35', 'he_100'],
                batch_size=200,
            )

        # Registros SS en dias feriado tambien se marcan (presencia sin salida)
        ss_registros = RegistroTareo.objects.filter(
            importacion_id=IMPORTACION_ASISTENCIA_ID,
            fecha__in=fechas_feriado,
            codigo_dia='SS',
            es_feriado=False,
        )
        ss_count = ss_registros.count()
        if not self.dry:
            ss_registros.update(es_feriado=True)

        self.stdout.write(
            f'  Registros T corregidos : {corregidos}\n'
            f'  Registros SS marcados  : {ss_count}\n'
            f'  HE25 liberadas         : {he_25_liberadas:>8.2f}h\n'
            f'  HE35 liberadas         : {he_35_liberadas:>8.2f}h\n'
            f'  HE100 reconocidas      : {he_100_ganadas:>8.2f}h'
        )

    # ------------------------------------------------------------------
    # 3. CREAR REGISTROS DS PARA DIAS DE DESCANSO COMPENSATORIO
    # ------------------------------------------------------------------

    def _crear_ds_compensacion(self):
        from personal.models import Personal
        from asistencia.models import RegistroTareo, TareoImportacion

        self.stdout.write('\n[3/4] Creando registros DS para dias de descanso compensatorio...')

        importacion = TareoImportacion.objects.get(pk=IMPORTACION_ASISTENCIA_ID)
        personal_map = {p.pk: p for p in Personal.objects.all()}

        # ── STAFF que trabajaron 02/abr → descanso el 04/abr ─────────────────
        staff_trab_abr2 = set(
            RegistroTareo.objects.filter(
                importacion_id=IMPORTACION_ASISTENCIA_ID,
                fecha=date(2026, 4, 2),
                codigo_dia__in=['T', 'SS'],
                grupo='STAFF',
            ).values_list('personal_id', flat=True).distinct()
        )
        # Los que NO tienen registro el 04/abr (tomaron descanso)
        con_abr4 = set(
            RegistroTareo.objects.filter(
                importacion_id=IMPORTACION_ASISTENCIA_ID,
                fecha=date(2026, 4, 4),
                personal_id__in=staff_trab_abr2,
            ).values_list('personal_id', flat=True).distinct()
        )
        staff_sin_abr4 = staff_trab_abr2 - con_abr4

        ds_abr4 = self._bulk_crear_ds(
            personal_ids=staff_sin_abr4,
            fecha=date(2026, 4, 4),
            fuente='COMP_FERIADO_02ABR',
            importacion=importacion,
            personal_map=personal_map,
        )
        self.stdout.write(f'  DS 04-abr (STAFF descanso por 02-abr): {ds_abr4} registros')

        # ── FORANEO que trabajaron 03/abr → descanso 4h el 05/abr ───────────
        for_trab_abr3 = set(
            RegistroTareo.objects.filter(
                importacion_id=IMPORTACION_ASISTENCIA_ID,
                fecha=date(2026, 4, 3),
                codigo_dia__in=['T', 'SS'],
                condicion='FORANEO',
            ).values_list('personal_id', flat=True).distinct()
        )

        con_abr5 = set(
            RegistroTareo.objects.filter(
                importacion_id=IMPORTACION_ASISTENCIA_ID,
                fecha=date(2026, 4, 5),
                personal_id__in=for_trab_abr3,
            ).values_list('personal_id', flat=True).distinct()
        )
        for_sin_abr5 = for_trab_abr3 - con_abr5
        ds_abr5 = self._bulk_crear_ds(
            personal_ids=for_sin_abr5,
            fecha=date(2026, 4, 5),
            fuente='COMP_FERIADO_03ABR_P1',
            importacion=importacion,
            personal_map=personal_map,
            horas_override=4.0,     # Solo 4h de compensacion
        )
        self.stdout.write(f'  DS 05-abr (FORANEO 4h comp por 03-abr): {ds_abr5} registros')

        # ── FORANEO descanso 4h el 12/abr ────────────────────────────────────
        con_abr12 = set(
            RegistroTareo.objects.filter(
                importacion_id=IMPORTACION_ASISTENCIA_ID,
                fecha=date(2026, 4, 12),
                personal_id__in=for_trab_abr3,
            ).values_list('personal_id', flat=True).distinct()
        )
        for_sin_abr12 = for_trab_abr3 - con_abr12
        ds_abr12 = self._bulk_crear_ds(
            personal_ids=for_sin_abr12,
            fecha=date(2026, 4, 12),
            fuente='COMP_FERIADO_03ABR_P2',
            importacion=importacion,
            personal_map=personal_map,
            horas_override=4.0,     # Solo 4h de compensacion
        )
        self.stdout.write(f'  DS 12-abr (FORANEO 4h comp por 03-abr): {ds_abr12} registros')

    def _bulk_crear_ds(
        self,
        personal_ids: set,
        fecha: date,
        fuente: str,
        importacion,
        personal_map: dict,
        horas_override: float | None = None,
    ) -> int:
        from asistencia.models import RegistroTareo

        if not personal_ids:
            return 0

        creados = 0
        for pid in personal_ids:
            p = personal_map.get(pid)
            if not p:
                continue

            # Determinar condicion y jornada del dia
            cond_raw = (p.condicion or 'LOCAL').upper()
            if 'FORANEO' in cond_raw or 'FORÁNEO' in cond_raw:
                condicion = 'FORANEO'
            elif cond_raw == 'LIMA':
                condicion = 'LIMA'
            else:
                condicion = 'LOCAL'

            horas = horas_override if horas_override is not None else _jornada(condicion, fecha)
            horas_d = Decimal(str(round(horas, 2)))

            if not self.dry:
                RegistroTareo.objects.get_or_create(
                    importacion=importacion,
                    personal=p,
                    fecha=fecha,
                    defaults=dict(
                        dni=p.nro_doc,
                        condicion=condicion,
                        grupo=p.grupo_tareo or 'STAFF',
                        codigo_dia='DS',
                        fuente_codigo=fuente[:30],
                        es_feriado=False,
                        horas_marcadas=Decimal('0'),
                        horas_efectivas=horas_d,
                        horas_normales=horas_d,
                        he_25=Decimal('0'),
                        he_35=Decimal('0'),
                        he_100=Decimal('0'),
                        he_al_banco=False,
                        almuerzo_manual=Decimal('0'),
                        dia_semana=fecha.weekday(),
                    )
                )
            creados += 1

        return creados

    # ------------------------------------------------------------------
    # 4. RECALCULAR BANCO DE HORAS STAFF AFECTADOS
    # ------------------------------------------------------------------

    def _recalc_banco(self):
        from asistencia.models import RegistroTareo, BancoHoras
        from django.db.models import Sum

        self.stdout.write('\n[4/4] Recalculando BancoHoras STAFF afectados (abril 2026)...')

        # Empleados STAFF con registros en 2/abr o 3/abr (los que cambiaron HE)
        pids_afectados = set(
            RegistroTareo.objects.filter(
                importacion_id=IMPORTACION_ASISTENCIA_ID,
                fecha__in=[date(2026, 4, 2), date(2026, 4, 3)],
                codigo_dia='T',
                grupo='STAFF',
            ).values_list('personal_id', flat=True).distinct()
        )

        if not pids_afectados:
            self.stdout.write('  Sin empleados STAFF afectados.')
            return

        # Recalcular BancoHoras de cada uno sumando TODOS sus registros de abril
        actualizados = 0
        for pid in pids_afectados:
            qs = RegistroTareo.objects.filter(
                importacion_id=IMPORTACION_ASISTENCIA_ID,
                personal_id=pid,
                grupo='STAFF',
                fecha__year=2026,
                fecha__month=4,
            ).aggregate(
                total_25=Sum('he_25'),
                total_35=Sum('he_35'),
                total_100=Sum('he_100'),
            )

            he25  = qs['total_25']  or Decimal('0')
            he35  = qs['total_35']  or Decimal('0')
            he100 = qs['total_100'] or Decimal('0')
            saldo = he25 + he35 + he100

            if not self.dry:
                banco, _ = BancoHoras.objects.get_or_create(
                    personal_id=pid,
                    periodo_anio=2026,
                    periodo_mes=4,
                    defaults={
                        'he_25_acumuladas':  he25,
                        'he_35_acumuladas':  he35,
                        'he_100_acumuladas': he100,
                        'saldo_horas':       saldo,
                        'cerrado':           False,
                        'observaciones':     'Recalculado: fix_semana_santa_2026',
                    }
                )
                if _:
                    pass  # recien creado, ya tiene los valores
                else:
                    # Actualizar si ya existia
                    banco.he_25_acumuladas  = he25
                    banco.he_35_acumuladas  = he35
                    banco.he_100_acumuladas = he100
                    banco.he_compensadas    = banco.he_compensadas  # no tocar
                    banco.saldo_horas       = saldo - banco.he_compensadas
                    banco.observaciones     = (banco.observaciones or '') + ' | fix_semana_santa_2026'
                    banco.save(update_fields=[
                        'he_25_acumuladas', 'he_35_acumuladas', 'he_100_acumuladas',
                        'saldo_horas', 'observaciones'
                    ])
            actualizados += 1

        self.stdout.write(f'  BancoHoras actualizados: {actualizados} empleados STAFF')
