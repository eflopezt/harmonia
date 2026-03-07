"""
seed_modulos_completos.py
Genera datos demo completos para todos los modulos vacios de Harmoni:
  - Vacaciones: TipoPermiso, SolicitudPermiso, SolicitudVacacion, VentaVacaciones
  - Evaluaciones: Evaluacion, RespuestaEvaluacion, ResultadoConsolidado
  - PDI/OKR: PlanDesarrollo, AccionDesarrollo, ObjetivoClave, ResultadoClave
  - Encuestas: RespuestaEncuesta (respuestas masivas a las 2 encuestas existentes)
  - Reclutamiento: Postulacion, EntrevistaPrograma
  - Onboarding: PlantillaOnboarding, PasoPlantilla, ProcesoOnboarding, PasoOnboarding
  - Viaticos: ConceptoViatico, AsignacionViatico, GastoViatico
  - Comunicaciones: ComunicadoMasivo, ConfirmacionLectura
  - Salarios: SimulacionIncremento, DetalleSimulacion
  - Capacitaciones: RequerimientoCapacitacion, CertificacionTrabajador

Idempotente: se puede ejecutar varias veces.
"""
import random
from datetime import date, timedelta, datetime
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils import timezone

from personal.models import Personal, Area

random.seed(42)


def rand_date(start, end):
    """Fecha aleatoria entre start y end."""
    delta = (end - start).days
    if delta <= 0:
        return start
    return start + timedelta(days=random.randint(0, delta))


def rand_decimal(lo, hi, decimals=2):
    val = random.uniform(float(lo), float(hi))
    return round(Decimal(str(val)), decimals)


class Command(BaseCommand):
    help = 'Genera datos demo completos para todos los modulos de Harmoni'

    def handle(self, *args, **options):
        self.stdout.write('\n=== SEED MODULOS COMPLETOS ===\n')

        # Obtener personal activo
        personal_qs = list(Personal.objects.filter(estado='Activo').order_by('id')[:280])
        if not personal_qs:
            self.stdout.write('[ERROR] No hay personal activo. Ejecutar loaddata empleados.json primero.')
            return

        areas_qs = list(Area.objects.all()[:20])
        self.stdout.write(f'  Personal activo: {len(personal_qs)}')
        self.stdout.write(f'  Areas: {len(areas_qs)}')

        # Obtener usuario admin para FK de auditoria
        from django.contrib.auth import get_user_model
        User = get_user_model()
        admin_user = User.objects.filter(is_superuser=True).first()
        if not admin_user:
            admin_user = User.objects.first()

        # ---------------------------------------------------------
        self._seed_tipo_permiso()
        self._seed_solicitudes_permiso(personal_qs, admin_user)
        self._seed_solicitudes_vacacion(personal_qs, admin_user)
        self._seed_venta_vacaciones(personal_qs, admin_user)
        self._seed_evaluaciones(personal_qs, admin_user)
        self._seed_planes_desarrollo(personal_qs, admin_user)
        self._seed_okrs(personal_qs, areas_qs, admin_user)
        self._seed_respuestas_encuesta(personal_qs)
        self._seed_postulaciones()
        self._seed_onboarding(personal_qs, admin_user)
        self._seed_viaticos(personal_qs, admin_user)
        self._seed_comunicados(areas_qs, personal_qs, admin_user)
        self._seed_simulaciones(personal_qs, admin_user)
        self._seed_requerimientos_capacitacion(areas_qs)
        self._seed_certificaciones(personal_qs)

        self.stdout.write('\n=== SEED COMPLETADO ===\n')

    # ----------------------------------------------------------------
    # TIPO PERMISO (12 tipos Peru)
    # ----------------------------------------------------------------
    def _seed_tipo_permiso(self):
        from vacaciones.models import TipoPermiso
        tipos = [
            ('Vacaciones', 'vacaciones', 30, True, False, True, 10),
            ('Licencia por Maternidad', 'maternidad', 98, True, True, False, 20),
            ('Licencia por Paternidad', 'paternidad', 10, True, True, False, 30),
            ('Permiso por Fallecimiento', 'fallecimiento', 5, True, True, False, 40),
            ('Permiso por Matrimonio', 'matrimonio', 5, True, False, False, 50),
            ('Permiso Medico', 'medico', 30, True, True, False, 60),
            ('Permiso Sindical', 'sindical', 30, True, True, False, 70),
            ('Permiso sin Goce de Haber', 'sin-goce', 30, False, False, False, 80),
            ('Licencia por Adopcion', 'adopcion', 30, True, True, False, 90),
            ('Permiso por Donacion de Sangre', 'donacion-sangre', 1, True, False, False, 100),
            ('Permiso por Capacitacion', 'capacitacion', 5, True, False, False, 110),
            ('Licencia por Accidente de Trabajo', 'accidente-trabajo', 365, True, True, False, 120),
        ]
        created = 0
        for nombre, codigo, dias_max, pagado, req_sust, desc_vac, orden in tipos:
            _, c = TipoPermiso.objects.get_or_create(
                codigo=codigo,
                defaults=dict(
                    nombre=nombre,
                    dias_max=dias_max,
                    pagado=pagado,
                    requiere_sustento=req_sust,
                    descuenta_vacaciones=desc_vac,
                    orden=orden,
                    activo=True,
                )
            )
            if c:
                created += 1
        self.stdout.write(f'  [OK] TipoPermiso: {created} creados')

    # ----------------------------------------------------------------
    # SOLICITUDES PERMISO
    # ----------------------------------------------------------------
    def _seed_solicitudes_permiso(self, personal_qs, admin_user):
        from vacaciones.models import SolicitudPermiso, TipoPermiso
        tipos = list(TipoPermiso.objects.filter(activo=True))
        if not tipos:
            return
        target = 60
        existing = SolicitudPermiso.objects.count()
        if existing >= target:
            self.stdout.write(f'  [SKIP] SolicitudPermiso: ya existen {existing}')
            return

        estados = ['APROBADA'] * 5 + ['COMPLETADA'] * 3 + ['PENDIENTE'] * 2
        created = 0
        base = date(2025, 1, 1)
        end = date(2026, 2, 28)
        sample = random.sample(personal_qs, min(50, len(personal_qs)))

        for i, p in enumerate(sample):
            tipo = random.choice(tipos[:6])  # tipos mas comunes
            fi = rand_date(base, end)
            dias = random.randint(1, min(tipo.dias_max or 5, 10))
            ff = fi + timedelta(days=dias - 1)
            estado = random.choice(estados)
            try:
                SolicitudPermiso.objects.get_or_create(
                    personal=p,
                    fecha_inicio=fi,
                    defaults=dict(
                        tipo=tipo,
                        fecha_fin=ff,
                        dias=dias,
                        motivo=f'Solicitud de {tipo.nombre.lower()} justificada',
                        estado=estado,
                        aprobado_por=admin_user if estado in ('APROBADA', 'COMPLETADA', 'RECHAZADA') else None,
                        fecha_aprobacion=fi - timedelta(days=2) if estado in ('APROBADA', 'COMPLETADA') else None,
                        solicitado_por=admin_user,
                    )
                )
                created += 1
            except Exception:
                pass
        self.stdout.write(f'  [OK] SolicitudPermiso: {created} creados')

    # ----------------------------------------------------------------
    # SOLICITUDES VACACION
    # ----------------------------------------------------------------
    def _seed_solicitudes_vacacion(self, personal_qs, admin_user):
        from vacaciones.models import SolicitudVacacion, SaldoVacacional
        target = 50
        existing = SolicitudVacacion.objects.count()
        if existing >= target:
            self.stdout.write(f'  [SKIP] SolicitudVacacion: ya existen {existing}')
            return

        saldos = list(
            SaldoVacacional.objects.filter(
                dias_pendientes__gte=7
            ).select_related('personal')[:100]
        )
        if not saldos:
            self.stdout.write('  [WARN] No hay SaldoVacacional con dias pendientes')
            return

        estados = ['APROBADA', 'APROBADA', 'COMPLETADA', 'COMPLETADA', 'COMPLETADA',
                   'PENDIENTE', 'EN_GOCE', 'RECHAZADA']
        created = 0
        for saldo in saldos[:50]:
            dias = random.randint(7, min(saldo.dias_pendientes, 15))
            fi = rand_date(date(2025, 1, 1), date(2026, 1, 31))
            ff = fi + timedelta(days=dias - 1)
            estado = random.choice(estados)
            try:
                SolicitudVacacion.objects.get_or_create(
                    personal=saldo.personal,
                    fecha_inicio=fi,
                    defaults=dict(
                        saldo=saldo,
                        fecha_fin=ff,
                        dias_calendario=dias,
                        motivo='Vacaciones programadas anuales',
                        estado=estado,
                        aprobado_por=admin_user if estado != 'PENDIENTE' else None,
                        fecha_aprobacion=fi - timedelta(days=3) if estado not in ('PENDIENTE', 'BORRADOR') else None,
                        solicitado_por=admin_user,
                    )
                )
                created += 1
            except Exception:
                pass
        self.stdout.write(f'  [OK] SolicitudVacacion: {created} creados')

    # ----------------------------------------------------------------
    # VENTA DE VACACIONES
    # ----------------------------------------------------------------
    def _seed_venta_vacaciones(self, personal_qs, admin_user):
        from vacaciones.models import VentaVacaciones, SaldoVacacional
        target = 25
        existing = VentaVacaciones.objects.count()
        if existing >= target:
            self.stdout.write(f'  [SKIP] VentaVacaciones: ya existen {existing}')
            return

        # Saldos con dias suficientes para vender
        saldos = list(
            SaldoVacacional.objects.filter(
                dias_pendientes__gte=15,
                estado__in=['PENDIENTE', 'PARCIAL']
            ).select_related('personal').order_by('-periodo_inicio')[:60]
        )
        created = 0
        for saldo in saldos[:25]:
            dias = random.randint(7, 15)
            # Calcular monto proporcional (sueldo / 30 * dias)
            remuneracion = saldo.personal.sueldo_base or Decimal('2000.00')
            monto = round(remuneracion / 30 * dias, 2)
            try:
                _, c = VentaVacaciones.objects.get_or_create(
                    personal=saldo.personal,
                    saldo=saldo,
                    defaults=dict(
                        dias_vendidos=dias,
                        monto=monto,
                        fecha=rand_date(date(2024, 7, 1), date(2025, 12, 31)),
                        aprobado_por=admin_user,
                    )
                )
                if c:
                    created += 1
            except Exception:
                pass
        self.stdout.write(f'  [OK] VentaVacaciones: {created} creados')

    # ----------------------------------------------------------------
    # EVALUACIONES
    # ----------------------------------------------------------------
    def _seed_evaluaciones(self, personal_qs, admin_user):
        from evaluaciones.models import (
            CicloEvaluacion, PlantillaEvaluacion, PlantillaCompetencia,
            Evaluacion, RespuestaEvaluacion, ResultadoConsolidado
        )
        ciclos = list(CicloEvaluacion.objects.all()[:2])
        if not ciclos:
            self.stdout.write('  [WARN] No hay CicloEvaluacion. Creando...')
            from evaluaciones.models import Competencia, PlantillaEvaluacion, PlantillaCompetencia
            self._crear_ciclos_y_plantillas(admin_user)
            ciclos = list(CicloEvaluacion.objects.all()[:2])
            if not ciclos:
                return

        plantillas = list(PlantillaEvaluacion.objects.filter(activa=True))
        if not plantillas:
            self.stdout.write('  [INFO] Creando PlantillaEvaluacion...')
            self._crear_ciclos_y_plantillas(admin_user)
            plantillas = list(PlantillaEvaluacion.objects.filter(activa=True))
        if not plantillas:
            self.stdout.write('  [WARN] No hay PlantillaEvaluacion activa')
            return

        existing = Evaluacion.objects.count()
        if existing >= 40:
            self.stdout.write(f'  [SKIP] Evaluacion: ya existen {existing}')
        else:
            ciclo = ciclos[0]
            plantilla = plantillas[0]
            items = list(PlantillaCompetencia.objects.filter(plantilla=plantilla))
            if not items:
                self.stdout.write('  [WARN] PlantillaCompetencia vacia')
                return

            # Seleccionar evaluados y evaluadores
            evaluados = random.sample(personal_qs, min(30, len(personal_qs)))
            supervisores = random.sample(personal_qs, min(5, len(personal_qs)))

            ev_created = 0
            resp_created = 0
            for evaluado in evaluados:
                # Autoevaluacion
                ev_auto, c = Evaluacion.objects.get_or_create(
                    ciclo=ciclo, evaluado=evaluado, relacion='AUTO',
                    defaults=dict(
                        evaluador=evaluado,
                        estado='COMPLETADA',
                        comentario_general='Autoevaluacion completada satisfactoriamente.',
                        fortalezas='Proactivo, orientado a resultados, buena comunicacion.',
                        areas_mejora='Gestion del tiempo y liderazgo en equipo.',
                        fecha_completada=timezone.now() - timedelta(days=random.randint(10, 60)),
                    )
                )
                if c:
                    ev_created += 1
                    puntaje_total = Decimal('0')
                    for item in items:
                        puntaje = rand_decimal(2.5, 5.0, 1)
                        RespuestaEvaluacion.objects.get_or_create(
                            evaluacion=ev_auto,
                            competencia_plantilla=item,
                            defaults=dict(puntaje=puntaje)
                        )
                        resp_created += 1
                        puntaje_total += puntaje * item.peso
                    if items:
                        peso_total = sum(i.peso for i in items)
                        ev_auto.puntaje_total = puntaje_total / peso_total if peso_total else puntaje_total
                        ev_auto.puntaje_calibrado = ev_auto.puntaje_total * Decimal('0.95')
                        ev_auto.save()

                # Evaluacion del jefe
                jefe = random.choice(supervisores)
                if jefe.id != evaluado.id:
                    ev_jefe, c = Evaluacion.objects.get_or_create(
                        ciclo=ciclo, evaluado=evaluado, relacion='JEFE',
                        defaults=dict(
                            evaluador=jefe,
                            estado='COMPLETADA',
                            comentario_general='Buen desempeno general, cumple objetivos del area.',
                            fortalezas='Disciplina, puntualidad y calidad de trabajo.',
                            areas_mejora='Puede mejorar en iniciativa y reporte de avances.',
                            fecha_completada=timezone.now() - timedelta(days=random.randint(5, 45)),
                        )
                    )
                    if c:
                        ev_created += 1
                        puntaje_total = Decimal('0')
                        for item in items:
                            puntaje = rand_decimal(3.0, 5.0, 1)
                            RespuestaEvaluacion.objects.get_or_create(
                                evaluacion=ev_jefe,
                                competencia_plantilla=item,
                                defaults=dict(puntaje=puntaje)
                            )
                            resp_created += 1
                            puntaje_total += puntaje * item.peso
                        if items:
                            peso_total = sum(i.peso for i in items)
                            ev_jefe.puntaje_total = puntaje_total / peso_total if peso_total else puntaje_total
                            ev_jefe.save()

            self.stdout.write(f'  [OK] Evaluacion: {ev_created} creados, RespuestaEvaluacion: {resp_created}')

        # ResultadoConsolidado (9-Box)
        existing_rc = ResultadoConsolidado.objects.count()
        if existing_rc < 25:
            ciclo = ciclos[0]
            muestra = random.sample(personal_qs, min(25, len(personal_qs)))
            rc_created = 0
            desempenos = ['BAJO', 'MEDIO', 'MEDIO', 'MEDIO', 'ALTO', 'ALTO']
            potenciales = ['BAJO', 'BAJO', 'MEDIO', 'MEDIO', 'ALTO', 'ALTO']
            nine_box_map = {
                ('BAJO', 'BAJO'): 1, ('BAJO', 'MEDIO'): 2, ('BAJO', 'ALTO'): 3,
                ('MEDIO', 'BAJO'): 4, ('MEDIO', 'MEDIO'): 5, ('MEDIO', 'ALTO'): 6,
                ('ALTO', 'BAJO'): 7, ('ALTO', 'MEDIO'): 8, ('ALTO', 'ALTO'): 9,
            }
            for p in muestra:
                desemp = random.choice(desempenos)
                potenc = random.choice(potenciales)
                _, c = ResultadoConsolidado.objects.get_or_create(
                    ciclo=ciclo, personal=p,
                    defaults=dict(
                        puntaje_promedio=rand_decimal(2.5, 4.8, 2),
                        puntaje_jefe=rand_decimal(3.0, 5.0, 2),
                        puntaje_auto=rand_decimal(2.8, 4.9, 2),
                        clasificacion_desempeno=desemp,
                        clasificacion_potencial=potenc,
                        nine_box_position=nine_box_map.get((desemp, potenc), 5),
                        observaciones='Resultado calibrado en sesion de comite RRHH.',
                        consolidado_por=admin_user,
                        fecha_consolidacion=timezone.now() - timedelta(days=random.randint(1, 30)),
                    )
                )
                if c:
                    rc_created += 1
            self.stdout.write(f'  [OK] ResultadoConsolidado: {rc_created} creados')
        else:
            self.stdout.write(f'  [SKIP] ResultadoConsolidado: ya existen {existing_rc}')

    def _crear_ciclos_y_plantillas(self, admin_user):
        """Crea ciclos y plantillas si no existen."""
        from evaluaciones.models import (
            Competencia, PlantillaEvaluacion, PlantillaCompetencia, CicloEvaluacion
        )
        competencias_data = [
            ('Liderazgo', 'liderazgo', 'LIDERAZGO'),
            ('Trabajo en Equipo', 'trabajo-equipo', 'INTERPERSONAL'),
            ('Orientacion a Resultados', 'orientacion-resultados', 'CORE'),
            ('Comunicacion Efectiva', 'comunicacion', 'INTERPERSONAL'),
            ('Innovacion y Mejora', 'innovacion', 'CORE'),
            ('Gestion del Tiempo', 'gestion-tiempo', 'CORE'),
        ]
        comps = []
        for nombre, codigo, cat in competencias_data:
            c, _ = Competencia.objects.get_or_create(
                codigo=codigo,
                defaults=dict(nombre=nombre, categoria=cat, activa=True, orden=10)
            )
            comps.append(c)

        plantilla, _ = PlantillaEvaluacion.objects.get_or_create(
            nombre='Evaluacion General 360',
            defaults=dict(
                escala_max=5,
                aplica_autoevaluacion=True,
                aplica_jefe=True,
                aplica_pares=True,
                activa=True,
            )
        )
        for i, comp in enumerate(comps):
            PlantillaCompetencia.objects.get_or_create(
                plantilla=plantilla,
                competencia=comp,
                defaults=dict(peso=Decimal('1.00'), orden=i * 10)
            )

        CicloEvaluacion.objects.get_or_create(
            nombre='Evaluacion Anual 2025',
            defaults=dict(
                tipo='360',
                plantilla=plantilla,
                fecha_inicio=date(2025, 10, 1),
                fecha_fin=date(2025, 11, 30),
                estado='CERRADO',
                creado_por=admin_user,
            )
        )
        CicloEvaluacion.objects.get_or_create(
            nombre='Evaluacion Semestral Q1 2026',
            defaults=dict(
                tipo='180',
                plantilla=plantilla,
                fecha_inicio=date(2026, 1, 15),
                fecha_fin=date(2026, 3, 15),
                estado='EN_EVALUACION',
                creado_por=admin_user,
            )
        )

    # ----------------------------------------------------------------
    # PLANES DE DESARROLLO INDIVIDUAL (PDI)
    # ----------------------------------------------------------------
    def _seed_planes_desarrollo(self, personal_qs, admin_user):
        from evaluaciones.models import PlanDesarrollo, AccionDesarrollo, CicloEvaluacion
        existing = PlanDesarrollo.objects.count()
        if existing >= 20:
            self.stdout.write(f'  [SKIP] PlanDesarrollo: ya existen {existing}')
            return

        ciclos = list(CicloEvaluacion.objects.all()[:1])
        ciclo = ciclos[0] if ciclos else None

        titulos = [
            'Desarrollo de Habilidades de Liderazgo',
            'Mejora en Comunicacion y Presentaciones',
            'Especializacion Tecnica en el Area',
            'Gestion de Proyectos y Equipos',
            'Certificacion en Seguridad y Salud Ocupacional',
            'Desarrollo de Competencias Digitales',
            'Plan de Carrera y Crecimiento Profesional',
            'Mejora en Gestion del Tiempo y Productividad',
        ]
        objetivos = [
            'Fortalecer competencias de liderazgo para asumir mayor responsabilidad.',
            'Mejorar habilidades de comunicacion oral y escrita en entornos laborales.',
            'Adquirir especializacion tecnica que agregue valor al equipo.',
            'Desarrollar capacidades de gestion de proyectos y liderazgo de equipos.',
            'Obtener certificacion SSOMA vigente segun Ley 29783.',
            'Dominar herramientas digitales clave para el puesto.',
            'Disenar plan de carrera con metas a corto y mediano plazo.',
            'Optimizar productividad personal y cumplimiento de plazos.',
        ]
        tipo_accion = ['CAPACITACION', 'PROYECTO', 'MENTORIA', 'LECTURA', 'PRACTICA']
        estados = ['ACTIVO', 'ACTIVO', 'ACTIVO', 'COMPLETADO', 'BORRADOR']

        muestra = random.sample(personal_qs, min(20, len(personal_qs)))
        created = 0
        for p in muestra:
            idx = random.randint(0, len(titulos) - 1)
            estado = random.choice(estados)
            fi = rand_date(date(2025, 1, 1), date(2025, 10, 1))
            ff = fi + timedelta(days=random.randint(90, 180))
            plan, c = PlanDesarrollo.objects.get_or_create(
                personal=p,
                titulo=titulos[idx],
                defaults=dict(
                    ciclo=ciclo,
                    objetivo=objetivos[idx],
                    estado=estado,
                    fecha_inicio=fi,
                    fecha_fin=ff,
                    responsable=admin_user,
                )
            )
            if c:
                created += 1
                # Crear 3-5 acciones
                for j in range(random.randint(3, 5)):
                    completada = (estado == 'COMPLETADO') or (j < 2 and estado == 'ACTIVO')
                    AccionDesarrollo.objects.get_or_create(
                        plan=plan,
                        descripcion=f'Accion {j + 1}: {random.choice(["Asistir a curso", "Desarrollar proyecto", "Leer documentacion", "Participar en taller", "Aplicar nuevos conocimientos"])} de {titulos[idx].lower()}',
                        defaults=dict(
                            tipo=random.choice(tipo_accion),
                            fecha_limite=fi + timedelta(days=(j + 1) * 30),
                            completada=completada,
                            fecha_completada=fi + timedelta(days=(j + 1) * 28) if completada else None,
                        )
                    )

        self.stdout.write(f'  [OK] PlanDesarrollo: {created} creados')

    # ----------------------------------------------------------------
    # OKRs
    # ----------------------------------------------------------------
    def _seed_okrs(self, personal_qs, areas_qs, admin_user):
        from evaluaciones.models import ObjetivoClave, ResultadoClave
        existing = ObjetivoClave.objects.count()
        if existing >= 15:
            self.stdout.write(f'  [SKIP] ObjetivoClave: ya existen {existing}')
            return

        okrs_empresa = [
            ('Incrementar la productividad operacional en un 15%', 'EMPRESA', 'ANUAL', 'ACTIVO'),
            ('Reducir la rotacion de personal a menos del 8% anual', 'EMPRESA', 'ANUAL', 'ACTIVO'),
            ('Lograr 95% de cumplimiento en capacitaciones SSOMA', 'EMPRESA', 'TRIMESTRAL', 'COMPLETADO'),
            ('Implementar sistema de evaluacion de desempeno al 100%', 'EMPRESA', 'SEMESTRAL', 'COMPLETADO'),
        ]
        okrs_area = [
            ('Reducir ausentismo del area al 3%', 'AREA', 'TRIMESTRAL', 'ACTIVO'),
            ('Completar onboarding de nuevos ingresos en menos de 30 dias', 'AREA', 'TRIMESTRAL', 'ACTIVO'),
            ('Mejorar indice de satisfaccion del equipo a 4.2/5', 'AREA', 'SEMESTRAL', 'EN_RIESGO'),
        ]
        okrs_individual = [
            ('Obtener certificacion tecnica relevante al puesto', 'INDIVIDUAL', 'ANUAL', 'ACTIVO'),
            ('Reducir errores en reportes a menos de 2 por mes', 'INDIVIDUAL', 'TRIMESTRAL', 'COMPLETADO'),
            ('Completar plan de desarrollo individual al 100%', 'INDIVIDUAL', 'ANUAL', 'EN_RIESGO'),
            ('Lograr 0 observaciones en auditoria SSOMA', 'INDIVIDUAL', 'TRIMESTRAL', 'ACTIVO'),
            ('Aumentar velocidad de proceso en 20%', 'INDIVIDUAL', 'TRIMESTRAL', 'ACTIVO'),
        ]

        created = 0
        objetos_empresa = []
        for titulo, nivel, periodo, status in okrs_empresa:
            trimestre = 1 if periodo == 'TRIMESTRAL' else None
            obj, c = ObjetivoClave.objects.get_or_create(
                titulo=titulo,
                defaults=dict(
                    nivel=nivel,
                    periodo=periodo,
                    anio=2026,
                    trimestre=trimestre,
                    status=status,
                    peso=Decimal('25.00'),
                    creado_por=admin_user,
                )
            )
            if c:
                created += 1
            objetos_empresa.append(obj)
            # KRs para empresa
            if ResultadoClave.objects.filter(objetivo=obj).count() == 0:
                krs_data = [
                    ('Productividad medida en tareas completadas por equipo', 'PORCENTAJE', 70, 85, 78),
                    ('Reduccion de tiempo de ciclo operativo (dias)', 'DIAS', 5, 3, 4),
                    ('NPS interno del area operativa', 'PUNTOS', 3.5, 5.0, 4.2),
                ]
                for desc, unidad, vi, vm, va in krs_data[:2]:
                    ResultadoClave.objects.create(
                        objetivo=obj,
                        descripcion=desc,
                        unidad=unidad,
                        valor_inicial=Decimal(str(vi)),
                        valor_meta=Decimal(str(vm)),
                        valor_actual=Decimal(str(va)),
                        fecha_limite=date(2026, 3, 31),
                    )

        # OKRs de area
        for i, (titulo, nivel, periodo, status) in enumerate(okrs_area):
            area = areas_qs[i % len(areas_qs)] if areas_qs else None
            trimestre = 1 if periodo == 'TRIMESTRAL' else None
            padre = objetos_empresa[0] if objetos_empresa else None
            obj, c = ObjetivoClave.objects.get_or_create(
                titulo=titulo,
                defaults=dict(
                    nivel=nivel,
                    area=area,
                    objetivo_padre=padre,
                    periodo=periodo,
                    anio=2026,
                    trimestre=trimestre,
                    status=status,
                    peso=Decimal('33.33'),
                    creado_por=admin_user,
                )
            )
            if c:
                created += 1
            if ResultadoClave.objects.filter(objetivo=obj).count() == 0:
                ResultadoClave.objects.create(
                    objetivo=obj,
                    descripcion='Porcentaje de cumplimiento del objetivo del area',
                    unidad='PORCENTAJE',
                    valor_inicial=Decimal('0.00'),
                    valor_meta=Decimal('100.00'),
                    valor_actual=Decimal(str(random.randint(45, 85))),
                    fecha_limite=date(2026, 3, 31),
                )

        # OKRs individuales
        muestra_ind = random.sample(personal_qs, min(len(okrs_individual), len(personal_qs)))
        for i, (titulo, nivel, periodo, status) in enumerate(okrs_individual):
            p = muestra_ind[i] if i < len(muestra_ind) else personal_qs[0]
            trimestre = random.randint(1, 2) if periodo == 'TRIMESTRAL' else None
            padre = objetos_empresa[i % len(objetos_empresa)] if objetos_empresa else None
            obj, c = ObjetivoClave.objects.get_or_create(
                titulo=titulo,
                personal=p,
                defaults=dict(
                    nivel=nivel,
                    objetivo_padre=padre,
                    periodo=periodo,
                    anio=2026,
                    trimestre=trimestre,
                    status=status,
                    peso=Decimal('25.00'),
                    creado_por=admin_user,
                )
            )
            if c:
                created += 1
            if ResultadoClave.objects.filter(objetivo=obj).count() == 0:
                ResultadoClave.objects.create(
                    objetivo=obj,
                    descripcion='Avance en el resultado clave principal',
                    unidad='PORCENTAJE',
                    valor_inicial=Decimal('0.00'),
                    valor_meta=Decimal('100.00'),
                    valor_actual=Decimal(str(random.randint(20, 90))),
                    responsable=p,
                    fecha_limite=date(2026, 3, 31) if trimestre == 1 else date(2026, 6, 30),
                )

        self.stdout.write(f'  [OK] ObjetivoClave: {created} creados')

    # ----------------------------------------------------------------
    # RESPUESTAS ENCUESTA
    # ----------------------------------------------------------------
    def _seed_respuestas_encuesta(self, personal_qs):
        from encuestas.models import Encuesta, PreguntaEncuesta, RespuestaEncuesta
        encuestas = list(Encuesta.objects.all()[:5])
        if not encuestas:
            self.stdout.write('  [WARN] No hay Encuesta. Creando...')
            self._crear_encuestas_base()
            encuestas = list(Encuesta.objects.all()[:5])
            if not encuestas:
                return

        total_created = 0
        for encuesta in encuestas:
            preguntas = list(PreguntaEncuesta.objects.filter(encuesta=encuesta))
            if not preguntas:
                continue
            existing = RespuestaEncuesta.objects.filter(encuesta=encuesta).count()
            if existing >= 80:
                self.stdout.write(f'  [SKIP] RespuestaEncuesta encuesta {encuesta.id}: ya existen {existing}')
                continue

            n_target = 100 if not encuesta.anonima else 120
            areas_list = ['Operaciones', 'Administracion', 'Recursos Humanos',
                          'Logistica', 'Finanzas', 'Seguridad', 'Produccion']
            grupos = ['STAFF', 'RCO']

            for i in range(n_target):
                respuestas_dict = {}
                for preg in preguntas:
                    if preg.tipo == 'ESCALA_5':
                        val = random.randint(2, 5)
                    elif preg.tipo == 'ESCALA_10':
                        # NPS: mas promotores que detractores para eNPS positivo
                        val = random.choices(
                            [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
                            weights=[1, 1, 1, 2, 2, 3, 4, 8, 12, 15, 10]
                        )[0]
                    elif preg.tipo == 'SI_NO':
                        val = random.choice(['Si', 'No'])
                    elif preg.tipo == 'OPCION' and preg.opciones:
                        val = random.choice(preg.opciones)
                    else:
                        val = random.randint(1, 5)
                    respuestas_dict[str(preg.pk)] = val

                personal = personal_qs[i % len(personal_qs)] if not encuesta.anonima else None
                comentarios = ''
                if random.random() < 0.3:
                    comentarios = random.choice([
                        'Buen ambiente de trabajo en general.',
                        'Mejorar la comunicacion entre areas.',
                        'El liderazgo ha mejorado notablemente.',
                        'Se necesitan mas capacitaciones tecnicas.',
                        'Conforme con los beneficios actuales.',
                        'La empresa ha crecido mucho este ano.',
                        '',
                    ])

                try:
                    RespuestaEncuesta.objects.create(
                        encuesta=encuesta,
                        personal=personal,
                        area_anonima=random.choice(areas_list) if encuesta.anonima else '',
                        grupo_anonimo=random.choice(grupos) if encuesta.anonima else '',
                        respuestas=respuestas_dict,
                        comentarios=comentarios,
                    )
                    total_created += 1
                except Exception:
                    pass

        self.stdout.write(f'  [OK] RespuestaEncuesta: {total_created} creadas')

    def _crear_encuestas_base(self):
        """Crea encuestas base si no existen."""
        from encuestas.models import Encuesta, PreguntaEncuesta
        enc1, _ = Encuesta.objects.get_or_create(
            titulo='Encuesta de Clima Laboral 2025',
            defaults=dict(
                tipo='CLIMA',
                estado='CERRADA',
                anonima=True,
                fecha_inicio=date(2025, 10, 1),
                fecha_fin=date(2025, 10, 31),
            )
        )
        preguntas_clima = [
            ('Como evaluas el ambiente de trabajo en tu equipo?', 'ESCALA_5', 'Ambiente'),
            ('Como calificarias la comunicacion con tu jefe directo?', 'ESCALA_5', 'Liderazgo'),
            ('Sientes que tu trabajo es reconocido?', 'ESCALA_5', 'Reconocimiento'),
            ('Que tan satisfecho estas con tu remuneracion actual?', 'ESCALA_5', 'Compensacion'),
            ('Recomendarias a Harmoni como lugar de trabajo? (0-10)', 'ESCALA_10', 'eNPS'),
        ]
        for i, (texto, tipo, cat) in enumerate(preguntas_clima):
            PreguntaEncuesta.objects.get_or_create(
                encuesta=enc1, orden=(i + 1) * 10,
                defaults=dict(texto=texto, tipo=tipo, categoria=cat, obligatoria=True)
            )

    # ----------------------------------------------------------------
    # POSTULACIONES Y ENTREVISTAS (RECLUTAMIENTO)
    # ----------------------------------------------------------------
    def _seed_postulaciones(self):
        from reclutamiento.models import Vacante, EtapaPipeline, Postulacion, EntrevistaPrograma
        from django.contrib.auth import get_user_model
        User = get_user_model()
        admin_user = User.objects.filter(is_superuser=True).first()

        vacantes = list(Vacante.objects.filter(estado__in=['PUBLICADA', 'EN_PROCESO'])[:10])
        if not vacantes:
            # Activar algunas vacantes existentes
            vacantes_borrador = list(Vacante.objects.all()[:10])
            for v in vacantes_borrador[:7]:
                v.estado = 'EN_PROCESO'
                v.publica = True
                v.fecha_publicacion = date(2025, 10, 1)
                v.fecha_limite = date(2026, 4, 30)
                v.save()
            vacantes = list(Vacante.objects.filter(estado='EN_PROCESO')[:10])

        if not vacantes:
            self.stdout.write('  [WARN] No hay vacantes para postulaciones')
            return

        etapas = list(EtapaPipeline.objects.filter(activa=True).order_by('orden'))
        if not etapas:
            self.stdout.write('  [WARN] No hay EtapaPipeline')
            return

        existing = Postulacion.objects.count()
        if existing >= 30:
            self.stdout.write(f'  [SKIP] Postulacion: ya existen {existing}')
            return

        candidatos = [
            ('Carlos Mendoza Torres', 'carlos.mendoza@gmail.com', '987654321', 'UNIVERSITARIO', 3, 'PORTAL'),
            ('Maria Quispe Flores', 'maria.quispe@hotmail.com', '976543210', 'UNIVERSITARIO', 5, 'LINKEDIN'),
            ('Jorge Ramirez Vega', 'jorge.ramirez@gmail.com', '965432109', 'MAESTRIA', 8, 'REFERIDO'),
            ('Ana Castillo Huaman', 'ana.castillo@outlook.com', '954321098', 'TECNICO', 2, 'PORTAL'),
            ('Luis Sanchez Prado', 'luis.sanchez@gmail.com', '943210987', 'UNIVERSITARIO', 4, 'LINKEDIN'),
            ('Rosa Garcia Paredes', 'rosa.garcia@gmail.com', '932109876', 'UNIVERSITARIO', 6, 'HEADHUNTER'),
            ('Pedro Torres Mamani', 'pedro.torres@gmail.com', '921098765', 'TECNICO', 1, 'PORTAL'),
            ('Carmen Valdivia Luna', 'carmen.valdivia@gmail.com', '910987654', 'UNIVERSITARIO', 7, 'REFERIDO'),
            ('Roberto Choque Arias', 'roberto.choque@gmail.com', '909876543', 'SECUNDARIA', 0, 'PORTAL'),
            ('Lucia Pacheco Silva', 'lucia.pacheco@gmail.com', '898765432', 'MAESTRIA', 10, 'HEADHUNTER'),
            ('Fernando Alva Rios', 'fernando.alva@gmail.com', '887654321', 'UNIVERSITARIO', 5, 'LINKEDIN'),
            ('Claudia Meza Duran', 'claudia.meza@gmail.com', '876543210', 'UNIVERSITARIO', 3, 'PORTAL'),
            ('Marco Soto Bustamante', 'marco.soto@gmail.com', '865432109', 'TECNICO', 2, 'REFERIDO'),
            ('Patricia Huanca Tito', 'patricia.huanca@gmail.com', '854321098', 'UNIVERSITARIO', 4, 'PORTAL'),
            ('Diego Apaza Condori', 'diego.apaza@gmail.com', '843210987', 'MAESTRIA', 6, 'LINKEDIN'),
        ]

        estados_post = ['ACTIVA'] * 8 + ['ACTIVA'] * 4 + ['DESCARTADA'] * 2 + ['CONTRATADA'] * 1
        created = 0
        postulaciones_list = []

        for i, (nombre, email, tel, edu, exp, fuente) in enumerate(candidatos):
            vacante = vacantes[i % len(vacantes)]
            etapa_idx = min(random.randint(0, len(etapas) - 1), len(etapas) - 1)
            etapa = etapas[etapa_idx]
            estado = estados_post[i % len(estados_post)]
            sal_pret = rand_decimal(2000, 8000, 2)
            p, c = Postulacion.objects.get_or_create(
                vacante=vacante,
                email=email,
                defaults=dict(
                    etapa=etapa,
                    nombre_completo=nombre,
                    telefono=tel,
                    educacion=edu,
                    experiencia_anos=exp,
                    salario_pretendido=sal_pret,
                    fuente=fuente,
                    estado=estado,
                    notas=f'Candidato con {exp} anios de experiencia. {random.choice(["Perfil alineado a la vacante.", "Experiencia relevante detectada.", "Requiere evaluacion tecnica.", "Muy buen perfil."])}',
                )
            )
            if c:
                created += 1
            postulaciones_list.append(p)

        self.stdout.write(f'  [OK] Postulacion: {created} creados')

        # Entrevistas
        existing_ent = EntrevistaPrograma.objects.count()
        if existing_ent >= 15:
            self.stdout.write(f'  [SKIP] EntrevistaPrograma: ya existen {existing_ent}')
            return

        tipos_ent = ['RRHH', 'TECNICA', 'GERENCIAL']
        resultados = ['APROBADO', 'APROBADO', 'RECHAZADO', 'PENDIENTE', 'PENDIENTE']
        ent_created = 0
        for post in postulaciones_list[:12]:
            tipo = random.choice(tipos_ent)
            resultado = random.choice(resultados)
            fecha_hora = timezone.now() - timedelta(days=random.randint(1, 30))
            try:
                EntrevistaPrograma.objects.get_or_create(
                    postulacion=post,
                    tipo=tipo,
                    defaults=dict(
                        fecha_hora=fecha_hora,
                        duracion_minutos=random.choice([45, 60, 90]),
                        entrevistador=admin_user,
                        modalidad=random.choice(['PRESENCIAL', 'VIRTUAL']),
                        ubicacion='Oficina RRHH - Piso 3' if random.random() > 0.5 else '',
                        resultado=resultado,
                        calificacion=random.randint(6, 10) if resultado == 'APROBADO' else random.randint(3, 6),
                        notas_post=f'Candidato {random.choice(["demuestra competencias clave", "tiene experiencia relevante", "buen manejo de situaciones de presion", "cumple con el perfil requerido"])}.',
                    )
                )
                ent_created += 1
            except Exception:
                pass

        self.stdout.write(f'  [OK] EntrevistaPrograma: {ent_created} creados')

    # ----------------------------------------------------------------
    # ONBOARDING
    # ----------------------------------------------------------------
    def _seed_onboarding(self, personal_qs, admin_user):
        from onboarding.models import (
            PlantillaOnboarding, PasoPlantilla,
            ProcesoOnboarding, PasoOnboarding
        )

        # Crear plantilla si no existe
        plt_staff, _ = PlantillaOnboarding.objects.get_or_create(
            nombre='Onboarding General STAFF',
            defaults=dict(
                descripcion='Proceso de incorporacion para personal STAFF.',
                aplica_grupo='STAFF',
                activa=True,
            )
        )
        pasos_staff = [
            (1, 'Bienvenida y presentacion de la empresa', 'TAREA', 'RRHH', 1),
            (2, 'Firma de contrato y documentos de ingreso', 'DOCUMENTO', 'RRHH', 1),
            (3, 'Alta en sistemas TI (correo, accesos)', 'TAREA', 'TI', 2),
            (4, 'Induccion SSOMA - Seguridad y Salud', 'CAPACITACION', 'RRHH', 3),
            (5, 'Presentacion al equipo y jefe directo', 'TAREA', 'JEFE', 1),
            (6, 'Entrega de EPP y uniformes', 'TAREA', 'RRHH', 2),
            (7, 'Revision de funciones y objetivos del puesto', 'TAREA', 'JEFE', 5),
            (8, 'Evaluacion del periodo de prueba (30 dias)', 'APROBACION', 'JEFE', 30),
        ]
        for orden, titulo, tipo, resp, dias in pasos_staff:
            PasoPlantilla.objects.get_or_create(
                plantilla=plt_staff, orden=orden,
                defaults=dict(titulo=titulo, tipo=tipo, responsable_tipo=resp, dias_plazo=dias, obligatorio=True)
            )

        plt_rco, _ = PlantillaOnboarding.objects.get_or_create(
            nombre='Onboarding Operativo RCO',
            defaults=dict(
                descripcion='Proceso de incorporacion para personal RCO operativo.',
                aplica_grupo='RCO',
                activa=True,
            )
        )
        pasos_rco = [
            (1, 'Registro en planilla y T-Registro', 'DOCUMENTO', 'RRHH', 1),
            (2, 'Induccion de seguridad en campo', 'CAPACITACION', 'RRHH', 1),
            (3, 'Entrega de EPP completo', 'TAREA', 'RRHH', 1),
            (4, 'Presentacion a supervisor directo', 'TAREA', 'JEFE', 1),
            (5, 'Registro biometrico y carnet de ingreso', 'TAREA', 'TI', 2),
            (6, 'Revision de reglamento interno', 'DOCUMENTO', 'TRABAJADOR', 3),
        ]
        for orden, titulo, tipo, resp, dias in pasos_rco:
            PasoPlantilla.objects.get_or_create(
                plantilla=plt_rco, orden=orden,
                defaults=dict(titulo=titulo, tipo=tipo, responsable_tipo=resp, dias_plazo=dias, obligatorio=True)
            )

        # Procesos de onboarding
        existing = ProcesoOnboarding.objects.count()
        if existing >= 15:
            self.stdout.write(f'  [SKIP] ProcesoOnboarding: ya existen {existing}')
            return

        # Trabajadores recientes (fecha_ingreso en los ultimos 12 meses)
        hoy = date.today()
        hace_1_anio = hoy - timedelta(days=365)
        recientes = [p for p in personal_qs if p.fecha_ingreso and p.fecha_ingreso >= hace_1_anio]
        if len(recientes) < 10:
            recientes = personal_qs[:15]

        estados_proc = ['COMPLETADO', 'COMPLETADO', 'COMPLETADO', 'EN_CURSO', 'EN_CURSO', 'CANCELADO']
        proc_created = 0
        paso_created = 0
        for p in recientes[:15]:
            plantilla = plt_staff if p.grupo_tareo == 'STAFF' else plt_rco
            fi = p.fecha_ingreso if p.fecha_ingreso else hoy - timedelta(days=random.randint(30, 300))
            estado_proc = random.choice(estados_proc)
            proc, c = ProcesoOnboarding.objects.get_or_create(
                personal=p,
                plantilla=plantilla,
                defaults=dict(
                    fecha_ingreso=fi,
                    fecha_inicio=fi,
                    estado=estado_proc,
                    iniciado_por=admin_user,
                    notas='Proceso iniciado por RRHH al momento del ingreso.',
                )
            )
            if c:
                proc_created += 1
                pasos_tmpl = list(plantilla.pasos.order_by('orden'))
                for j, paso_t in enumerate(pasos_tmpl):
                    es_completado = (estado_proc == 'COMPLETADO') or (j < len(pasos_tmpl) // 2 and estado_proc == 'EN_CURSO')
                    PasoOnboarding.objects.create(
                        proceso=proc,
                        paso_plantilla=paso_t,
                        orden=paso_t.orden,
                        titulo=paso_t.titulo,
                        estado='COMPLETADO' if es_completado else 'PENDIENTE',
                        fecha_limite=fi + timedelta(days=paso_t.dias_plazo),
                        fecha_completado=timezone.make_aware(datetime.combine(
                            fi + timedelta(days=paso_t.dias_plazo - 1), datetime.min.time()
                        )) if es_completado else None,
                    )
                    paso_created += 1

        self.stdout.write(f'  [OK] ProcesoOnboarding: {proc_created}, PasoOnboarding: {paso_created}')

    # ----------------------------------------------------------------
    # VIATICOS
    # ----------------------------------------------------------------
    def _seed_viaticos(self, personal_qs, admin_user):
        from viaticos.models import ConceptoViatico, AsignacionViatico, GastoViatico

        # Conceptos de viatico
        conceptos_data = [
            ('Hospedaje', 'hospedaje', Decimal('150.00'), True),
            ('Alimentacion', 'alimentacion', Decimal('60.00'), True),
            ('Movilidad Local', 'movilidad-local', Decimal('40.00'), False),
            ('Movilidad Interprovincial', 'movilidad-interprov', None, True),
            ('Comunicaciones', 'comunicaciones', Decimal('30.00'), False),
        ]
        conceptos = []
        for nombre, codigo, tope, req_comp in conceptos_data:
            c, _ = ConceptoViatico.objects.get_or_create(
                codigo=codigo,
                defaults=dict(nombre=nombre, tope_diario=tope, requiere_comprobante=req_comp, activo=True, orden=10)
            )
            conceptos.append(c)

        # Asignaciones
        existing = AsignacionViatico.objects.count()
        if existing >= 30:
            self.stdout.write(f'  [SKIP] AsignacionViatico: ya existen {existing}')
            return

        # Trabajadores foraneos (usar subset de personal)
        foraneos = [p for p in personal_qs if p.grupo_tareo == 'RCO'][:40]
        if len(foraneos) < 10:
            foraneos = personal_qs[:30]

        ubicaciones = [
            'Mina Julcani - Huancavelica',
            'Proyecto Antapaccay - Cusco',
            'Unidad Minera Chungar - Pasco',
            'Proyecto San Rafael - Puno',
            'Campamento Toquepala - Tacna',
        ]
        estados_via = ['CONCILIADO', 'CONCILIADO', 'ENTREGADO', 'EN_RENDICION', 'APROBADO', 'BORRADOR']

        avi_created = 0
        gasto_created = 0
        meses = [
            date(2025, 9, 1), date(2025, 10, 1), date(2025, 11, 1),
            date(2025, 12, 1), date(2026, 1, 1), date(2026, 2, 1),
        ]

        for i, p in enumerate(foraneos[:30]):
            periodo = meses[i % len(meses)]
            monto_base = rand_decimal(800, 3000, 2)
            estado = random.choice(estados_via)
            dias_campo = random.randint(15, 25)
            try:
                av, c = AsignacionViatico.objects.get_or_create(
                    personal=p,
                    periodo=periodo,
                    defaults=dict(
                        monto_asignado=monto_base,
                        ubicacion=random.choice(ubicaciones),
                        dias_campo=dias_campo,
                        estado=estado,
                        fecha_entrega=periodo + timedelta(days=3) if estado != 'BORRADOR' else None,
                        observaciones='Asignacion de viaticos para personal en campo.',
                        monto_rendido=monto_base * Decimal('0.95') if estado in ('CONCILIADO',) else Decimal('0.00'),
                        aprobado_por=admin_user if estado != 'BORRADOR' else None,
                        creado_por=admin_user,
                    )
                )
                if c:
                    avi_created += 1
                    # Gastos para los conciliados
                    if estado == 'CONCILIADO' and conceptos:
                        n_gastos = random.randint(3, 6)
                        for _ in range(n_gastos):
                            concepto = random.choice(conceptos)
                            monto_g = rand_decimal(30, min(float(concepto.tope_diario or 200), 200), 2)
                            GastoViatico.objects.create(
                                asignacion=av,
                                concepto=concepto,
                                fecha_gasto=periodo + timedelta(days=random.randint(1, 25)),
                                monto=monto_g,
                                descripcion=f'Gasto de {concepto.nombre.lower()} en campo',
                                tipo_comprobante=random.choice(['BOLETA', 'FACTURA', 'TICKET']),
                                numero_comprobante=f'B{random.randint(100, 999)}-{random.randint(1000, 9999)}',
                                estado='APROBADO',
                            )
                            gasto_created += 1
            except Exception:
                pass

        self.stdout.write(f'  [OK] AsignacionViatico: {avi_created}, GastoViatico: {gasto_created}')

    # ----------------------------------------------------------------
    # COMUNICADOS MASIVOS
    # ----------------------------------------------------------------
    def _seed_comunicados(self, areas_qs, personal_qs, admin_user):
        from comunicaciones.models import ComunicadoMasivo, ConfirmacionLectura
        existing = ComunicadoMasivo.objects.count()
        if existing >= 8:
            self.stdout.write(f'  [SKIP] ComunicadoMasivo: ya existen {existing}')
            return

        comunicados_data = [
            ('Politica de Seguridad y Salud Ocupacional 2026', 'POLITICA', 'TODOS', True),
            ('Comunicado: Incremento Salarial Enero 2026', 'COMUNICADO', 'TODOS', True),
            ('Memo: Nuevas Politicas de Uso de EPP', 'MEMO', 'GRUPO', True),
            ('Aviso: Cierre de Planilla - Enero 2026', 'AVISO', 'TODOS', False),
            ('Comunicado: Evaluacion de Desempeno Q1 2026', 'COMUNICADO', 'TODOS', True),
            ('Politica de Vacaciones y Permisos Actualizada', 'POLITICA', 'TODOS', True),
            ('Aviso: Mantenimiento del Sistema RRHH', 'AVISO', 'TODOS', False),
            ('Comunicado: Resultados Encuesta de Clima 2025', 'COMUNICADO', 'TODOS', False),
        ]

        cuerpo_template = (
            '<p>Estimado colaborador,</p>'
            '<p>Por medio del presente comunicado se informa sobre: <strong>{titulo}</strong>.</p>'
            '<p>Les pedimos tomar nota de las indicaciones y cumplir con lo estipulado.</p>'
            '<p>Ante cualquier consulta, comunicarse con el area de RRHH.</p>'
            '<p>Atentamente,<br/><strong>Gerencia de Recursos Humanos</strong></p>'
        )

        com_created = 0
        conf_created = 0
        for titulo, tipo, dest_tipo, req_conf in comunicados_data:
            grupo_val = 'RCO' if dest_tipo == 'GRUPO' else ''
            fecha_envio = timezone.now() - timedelta(days=random.randint(5, 60))
            com, c = ComunicadoMasivo.objects.get_or_create(
                titulo=titulo,
                defaults=dict(
                    cuerpo=cuerpo_template.format(titulo=titulo),
                    tipo=tipo,
                    estado='ENVIADO',
                    destinatarios_tipo=dest_tipo,
                    grupo=grupo_val,
                    requiere_confirmacion=req_conf,
                    enviado_en=fecha_envio,
                    creado_por=admin_user,
                )
            )
            if c:
                com_created += 1
                # Confirmaciones de lectura
                if req_conf:
                    n_conf = random.randint(30, min(80, len(personal_qs)))
                    muestra_conf = random.sample(personal_qs, n_conf)
                    for p in muestra_conf:
                        try:
                            ConfirmacionLectura.objects.get_or_create(
                                comunicado=com,
                                personal=p,
                                defaults=dict(confirmado=True)
                            )
                            conf_created += 1
                        except Exception:
                            pass

        self.stdout.write(f'  [OK] ComunicadoMasivo: {com_created}, ConfirmacionLectura: {conf_created}')

    # ----------------------------------------------------------------
    # SIMULACIONES DE INCREMENTO SALARIAL
    # ----------------------------------------------------------------
    def _seed_simulaciones(self, personal_qs, admin_user):
        from salarios.models import SimulacionIncremento, DetalleSimulacion

        existing = SimulacionIncremento.objects.count()
        if existing >= 3:
            self.stdout.write(f'  [SKIP] SimulacionIncremento: ya existen {existing}')
            return

        sims_data = [
            ('Incremento Anual 2026 - 5% General', date(2025, 12, 15), 'PORCENTAJE', 'APLICADA', Decimal('500000.00')),
            ('Ajuste de Mercado Q1 2026 - STAFF Senior', date(2026, 1, 20), 'PORCENTAJE', 'APROBADA', Decimal('150000.00')),
            ('Propuesta Incremento RCO - Monto Fijo', date(2026, 2, 10), 'MONTO_FIJO', 'BORRADOR', Decimal('200000.00')),
        ]

        for nombre, fecha, tipo_sim, estado, presupuesto in sims_data:
            sim, c = SimulacionIncremento.objects.get_or_create(
                nombre=nombre,
                defaults=dict(
                    fecha=fecha,
                    tipo=tipo_sim,
                    estado=estado,
                    presupuesto_total=presupuesto,
                    descripcion=f'Simulacion de {nombre.lower()} para planificacion presupuestal.',
                    creado_por=admin_user,
                )
            )
            if c:
                # Detalles: ~50-80 empleados
                n_emp = random.randint(50, min(80, len(personal_qs)))
                muestra_sim = random.sample(personal_qs, n_emp)
                det_created = 0
                for p in muestra_sim:
                    rem_actual = p.sueldo_base or Decimal('2000.00')
                    if tipo_sim == 'PORCENTAJE':
                        pct = rand_decimal(3, 8, 1)
                        incremento = round(rem_actual * pct / 100, 2)
                    else:
                        incremento = rand_decimal(100, 400, 2)
                    try:
                        DetalleSimulacion.objects.get_or_create(
                            simulacion=sim,
                            personal=p,
                            defaults=dict(
                                remuneracion_actual=rem_actual,
                                incremento_propuesto=incremento,
                                aprobado=True,
                            )
                        )
                        det_created += 1
                    except Exception:
                        pass
                self.stdout.write(f'  [OK] Simulacion "{nombre}": {det_created} detalles')

    # ----------------------------------------------------------------
    # REQUERIMIENTOS DE CAPACITACION
    # ----------------------------------------------------------------
    def _seed_requerimientos_capacitacion(self, areas_qs):
        from capacitaciones.models import CategoriaCapacitacion, RequerimientoCapacitacion
        existing = RequerimientoCapacitacion.objects.count()
        if existing >= 10:
            self.stdout.write(f'  [SKIP] RequerimientoCapacitacion: ya existen {existing}')
            return

        categorias = list(CategoriaCapacitacion.objects.all()[:6])
        cat_ssoma = next((c for c in categorias if 'ssoma' in c.codigo.lower() or 'segur' in c.nombre.lower()), None)
        cat_any = categorias[0] if categorias else None

        reqs_data = [
            ('Induccion General de Seguridad', True, 'UNICA', Decimal('8.0'), 'Ley 29783, DS 005-2012-TR', True, True, 365),
            ('IPERC - Identificacion de Peligros', True, 'ANUAL', Decimal('16.0'), 'DS 055-2010-EM', True, True, 365),
            ('Uso de EPP - Equipos de Proteccion Personal', True, 'ANUAL', Decimal('4.0'), 'Ley 29783', True, True, 365),
            ('Primeros Auxilios Basico', False, 'ANUAL', Decimal('8.0'), 'Ley 29783', True, True, 365),
            ('Manejo Defensivo', False, 'ANUAL', Decimal('16.0'), 'Reg. Transporte MTC', True, False, 365),
            ('Liderazgo y Gestion de Equipos', False, 'ANUAL', Decimal('20.0'), '', False, False, 730),
            ('Excel Avanzado para RRHH', False, 'SEMESTRAL', Decimal('16.0'), '', False, False, 180),
            ('Induccion al Sistema ERP Harmoni', True, 'UNICA', Decimal('4.0'), '', True, True, 730),
            ('Normativa Laboral Peruana', False, 'ANUAL', Decimal('8.0'), 'DL 728, Ley 29783', False, False, 365),
            ('Comunicacion Efectiva y Trabajo en Equipo', False, 'ANUAL', Decimal('12.0'), '', True, True, 365),
        ]

        created = 0
        for nombre, aplica_todos, frec, horas, base, staff, rco, vigencia in reqs_data:
            cat = cat_ssoma if 'Seguridad' in nombre or 'IPERC' in nombre or 'EPP' in nombre else cat_any
            r, c = RequerimientoCapacitacion.objects.get_or_create(
                nombre=nombre,
                defaults=dict(
                    categoria=cat,
                    aplica_todos=aplica_todos,
                    aplica_staff=staff,
                    aplica_rco=rco,
                    frecuencia=frec,
                    horas_minimas=horas,
                    vigencia_dias=vigencia,
                    base_legal=base,
                    obligatorio=aplica_todos,
                    activo=True,
                )
            )
            if c:
                created += 1
                if areas_qs and not aplica_todos:
                    r.aplica_areas.set(areas_qs[:3])

        self.stdout.write(f'  [OK] RequerimientoCapacitacion: {created} creados')

    # ----------------------------------------------------------------
    # CERTIFICACIONES DE TRABAJADOR
    # ----------------------------------------------------------------
    def _seed_certificaciones(self, personal_qs):
        from capacitaciones.models import (
            RequerimientoCapacitacion, Capacitacion, CertificacionTrabajador
        )
        existing = CertificacionTrabajador.objects.count()
        if existing >= 100:
            self.stdout.write(f'  [SKIP] CertificacionTrabajador: ya existen {existing}')
            return

        reqs = list(RequerimientoCapacitacion.objects.filter(activo=True)[:5])
        caps = list(Capacitacion.objects.filter(estado='COMPLETADA')[:6])

        if not reqs:
            self.stdout.write('  [WARN] No hay RequerimientoCapacitacion activo')
            return

        created = 0
        muestra = random.sample(personal_qs, min(100, len(personal_qs)))

        for p in muestra:
            req = random.choice(reqs)
            cap = random.choice(caps) if caps else None
            fecha_ob = rand_date(date(2024, 1, 1), date(2025, 12, 31))
            try:
                _, c = CertificacionTrabajador.objects.get_or_create(
                    personal=p,
                    requerimiento=req,
                    defaults=dict(
                        capacitacion=cap,
                        fecha_obtencion=fecha_ob,
                        # fecha_vencimiento calculado auto en save()
                    )
                )
                if c:
                    created += 1
            except Exception:
                pass

        self.stdout.write(f'  [OK] CertificacionTrabajador: {created} creados')
