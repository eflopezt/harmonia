"""
Tests para modelos del modulo evaluaciones de desempeno.
Valida competencias, plantillas, ciclos 360, evaluaciones, 9-Box, PDI y OKRs.
"""
import pytest
from datetime import date, timedelta
from decimal import Decimal
from django.contrib.auth.models import User

from personal.models import Area, SubArea, Personal
from evaluaciones.models import (
    Competencia, PlantillaEvaluacion, PlantillaCompetencia,
    CicloEvaluacion, Evaluacion, RespuestaEvaluacion,
    ResultadoConsolidado, PlanDesarrollo, AccionDesarrollo,
    ObjetivoClave, ResultadoClave, CheckInOKR,
)


@pytest.fixture
def area():
    return Area.objects.create(nombre='GERENCIA GENERAL')


@pytest.fixture
def personal(area):
    subarea = SubArea.objects.create(nombre='DIRECTORIO', area=area)
    return Personal.objects.create(
        nro_doc='33333333',
        apellidos_nombres='FERNANDEZ DIAZ MARIA',
        cargo='Gerente de Operaciones',
        tipo_trab='Empleado',
        subarea=subarea,
        estado='Activo',
    )


@pytest.fixture
def personal2(area):
    subarea = SubArea.objects.create(nombre='ADMINISTRACION', area=area)
    return Personal.objects.create(
        nro_doc='44444444',
        apellidos_nombres='ROJAS SILVA LUIS',
        cargo='Jefe Administrativo',
        tipo_trab='Empleado',
        subarea=subarea,
        estado='Activo',
    )


@pytest.fixture
def user():
    return User.objects.create_user(username='evaluador', password='test1234')


@pytest.fixture
def competencia_liderazgo():
    return Competencia.objects.create(
        nombre='Liderazgo', codigo='liderazgo',
        categoria='LIDERAZGO',
    )


@pytest.fixture
def competencia_tecnica():
    return Competencia.objects.create(
        nombre='Conocimiento Técnico', codigo='conocimiento-tecnico',
        categoria='TECNICA',
    )


@pytest.fixture
def plantilla(competencia_liderazgo, competencia_tecnica):
    p = PlantillaEvaluacion.objects.create(
        nombre='Evaluación Anual Estándar', escala_max=5,
    )
    PlantillaCompetencia.objects.create(
        plantilla=p, competencia=competencia_liderazgo,
        peso=Decimal('2.00'), orden=1,
    )
    PlantillaCompetencia.objects.create(
        plantilla=p, competencia=competencia_tecnica,
        peso=Decimal('3.00'), orden=2,
    )
    return p


@pytest.fixture
def ciclo(plantilla):
    return CicloEvaluacion.objects.create(
        nombre='Evaluación Anual 2026',
        tipo='180',
        plantilla=plantilla,
        fecha_inicio=date(2026, 1, 1),
        fecha_fin=date(2026, 1, 31),
    )


@pytest.fixture
def evaluacion(ciclo, personal, personal2):
    return Evaluacion.objects.create(
        ciclo=ciclo,
        evaluado=personal,
        evaluador=personal2,
        relacion='JEFE',
    )


# ──────────────────────────────────────────────────────────────
# Competencia
# ──────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestCompetencia:

    def test_crear_competencia(self, competencia_liderazgo):
        assert competencia_liderazgo.activa is True
        assert competencia_liderazgo.categoria == 'LIDERAZGO'
        assert str(competencia_liderazgo) == 'Liderazgo'

    def test_codigo_unique(self, competencia_liderazgo):
        from django.db import IntegrityError
        with pytest.raises(IntegrityError):
            Competencia.objects.create(nombre='Otro', codigo='liderazgo')


# ──────────────────────────────────────────────────────────────
# PlantillaEvaluacion
# ──────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestPlantillaEvaluacion:

    def test_crear_plantilla(self, plantilla):
        assert plantilla.escala_max == 5
        assert plantilla.aplica_autoevaluacion is True
        assert plantilla.aplica_jefe is True
        assert plantilla.aplica_pares is False
        assert str(plantilla) == 'Evaluación Anual Estándar'

    def test_competencias_through(self, plantilla):
        items = plantilla.items.all()
        assert items.count() == 2
        assert items[0].peso == Decimal('2.00')
        assert items[1].peso == Decimal('3.00')

    def test_plantilla_competencia_str(self, plantilla):
        item = plantilla.items.first()
        s = str(item)
        assert 'Evaluación Anual Estándar' in s
        assert 'x2' in s

    def test_unique_together_plantilla_competencia(self, plantilla, competencia_liderazgo):
        from django.db import IntegrityError
        with pytest.raises(IntegrityError):
            PlantillaCompetencia.objects.create(
                plantilla=plantilla, competencia=competencia_liderazgo,
                peso=Decimal('1.00'),
            )


# ──────────────────────────────────────────────────────────────
# CicloEvaluacion
# ──────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestCicloEvaluacion:

    def test_crear_ciclo(self, ciclo):
        assert ciclo.estado == 'BORRADOR'
        assert ciclo.tipo == '180'
        assert '180' in str(ciclo)

    def test_total_evaluaciones_vacio(self, ciclo):
        assert ciclo.total_evaluaciones == 0

    def test_porcentaje_avance_sin_evaluaciones(self, ciclo):
        assert ciclo.porcentaje_avance == 0

    def test_porcentaje_avance_con_evaluaciones(self, ciclo, personal, personal2):
        Evaluacion.objects.create(
            ciclo=ciclo, evaluado=personal, relacion='AUTO',
            estado='COMPLETADA',
        )
        Evaluacion.objects.create(
            ciclo=ciclo, evaluado=personal2, relacion='AUTO',
            estado='PENDIENTE',
        )
        assert ciclo.total_evaluaciones == 2
        assert ciclo.completadas == 1
        assert ciclo.porcentaje_avance == 50


# ──────────────────────────────────────────────────────────────
# Evaluacion y calculo de puntaje ponderado
# ──────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestEvaluacion:

    def test_crear_evaluacion(self, evaluacion):
        assert evaluacion.estado == 'PENDIENTE'
        assert evaluacion.relacion == 'JEFE'
        assert evaluacion.puntaje_total is None

    def test_str(self, evaluacion):
        s = str(evaluacion)
        assert 'FERNANDEZ DIAZ MARIA' in s
        assert 'Jefe' in s

    def test_puntaje_final_usa_calibrado(self, evaluacion):
        evaluacion.puntaje_total = Decimal('4.00')
        evaluacion.puntaje_calibrado = Decimal('4.50')
        assert evaluacion.puntaje_final == Decimal('4.50')

    def test_puntaje_final_fallback_a_total(self, evaluacion):
        evaluacion.puntaje_total = Decimal('3.80')
        evaluacion.puntaje_calibrado = None
        assert evaluacion.puntaje_final == Decimal('3.80')

    def test_calcular_puntaje_sin_respuestas(self, evaluacion):
        result = evaluacion.calcular_puntaje()
        assert result is None

    def test_calcular_puntaje_ponderado(self, evaluacion, plantilla):
        """
        Liderazgo: peso=2, puntaje=4
        Tecnica:   peso=3, puntaje=5
        Ponderado: (4*2 + 5*3) / (2+3) = 23/5 = 4.60
        """
        items = plantilla.items.all().order_by('orden')
        RespuestaEvaluacion.objects.create(
            evaluacion=evaluacion,
            competencia_plantilla=items[0],  # Liderazgo
            puntaje=Decimal('4.0'),
        )
        RespuestaEvaluacion.objects.create(
            evaluacion=evaluacion,
            competencia_plantilla=items[1],  # Técnica
            puntaje=Decimal('5.0'),
        )
        resultado = evaluacion.calcular_puntaje()
        assert resultado == Decimal('4.60')
        evaluacion.refresh_from_db()
        assert evaluacion.puntaje_total == Decimal('4.60')


# ──────────────────────────────────────────────────────────────
# RespuestaEvaluacion
# ──────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestRespuestaEvaluacion:

    def test_unique_together(self, evaluacion, plantilla):
        item = plantilla.items.first()
        RespuestaEvaluacion.objects.create(
            evaluacion=evaluacion, competencia_plantilla=item,
            puntaje=Decimal('4.0'),
        )
        from django.db import IntegrityError
        with pytest.raises(IntegrityError):
            RespuestaEvaluacion.objects.create(
                evaluacion=evaluacion, competencia_plantilla=item,
                puntaje=Decimal('3.0'),
            )

    def test_str(self, evaluacion, plantilla):
        item = plantilla.items.first()
        r = RespuestaEvaluacion.objects.create(
            evaluacion=evaluacion, competencia_plantilla=item,
            puntaje=Decimal('4.5'),
        )
        assert '4.5' in str(r)


# ──────────────────────────────────────────────────────────────
# ResultadoConsolidado (9-Box)
# ──────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestResultadoConsolidado:

    def test_calcular_nine_box_alto_alto(self, ciclo, personal):
        r = ResultadoConsolidado.objects.create(
            ciclo=ciclo, personal=personal,
            clasificacion_desempeno='ALTO',
            clasificacion_potencial='ALTO',
        )
        pos = r.calcular_nine_box()
        assert pos == 9

    def test_calcular_nine_box_bajo_bajo(self, ciclo, personal):
        r = ResultadoConsolidado.objects.create(
            ciclo=ciclo, personal=personal,
            clasificacion_desempeno='BAJO',
            clasificacion_potencial='BAJO',
        )
        assert r.calcular_nine_box() == 1

    def test_calcular_nine_box_medio_alto(self, ciclo, personal):
        r = ResultadoConsolidado.objects.create(
            ciclo=ciclo, personal=personal,
            clasificacion_desempeno='MEDIO',
            clasificacion_potencial='ALTO',
        )
        assert r.calcular_nine_box() == 6

    def test_nine_box_todas_combinaciones(self, ciclo, personal):
        """Verifica las 9 posiciones del 9-Box."""
        esperado = {
            ('BAJO', 'BAJO'): 1, ('BAJO', 'MEDIO'): 2, ('BAJO', 'ALTO'): 3,
            ('MEDIO', 'BAJO'): 4, ('MEDIO', 'MEDIO'): 5, ('MEDIO', 'ALTO'): 6,
            ('ALTO', 'BAJO'): 7, ('ALTO', 'MEDIO'): 8, ('ALTO', 'ALTO'): 9,
        }
        for (desemp, potenc), posicion in esperado.items():
            r = ResultadoConsolidado(
                ciclo=ciclo, personal=personal,
                clasificacion_desempeno=desemp,
                clasificacion_potencial=potenc,
            )
            # Calcular sin save (para no violar unique_together)
            mapping = {
                ('BAJO', 'BAJO'): 1, ('BAJO', 'MEDIO'): 2, ('BAJO', 'ALTO'): 3,
                ('MEDIO', 'BAJO'): 4, ('MEDIO', 'MEDIO'): 5, ('MEDIO', 'ALTO'): 6,
                ('ALTO', 'BAJO'): 7, ('ALTO', 'MEDIO'): 8, ('ALTO', 'ALTO'): 9,
            }
            key = (r.clasificacion_desempeno, r.clasificacion_potencial)
            assert mapping.get(key) == posicion

    def test_str(self, ciclo, personal):
        r = ResultadoConsolidado.objects.create(
            ciclo=ciclo, personal=personal,
        )
        s = str(r)
        assert 'FERNANDEZ DIAZ MARIA' in s
        assert 'Evaluación Anual 2026' in s

    def test_unique_together_ciclo_personal(self, ciclo, personal):
        ResultadoConsolidado.objects.create(ciclo=ciclo, personal=personal)
        from django.db import IntegrityError
        with pytest.raises(IntegrityError):
            ResultadoConsolidado.objects.create(ciclo=ciclo, personal=personal)


# ──────────────────────────────────────────────────────────────
# PlanDesarrollo (PDI)
# ──────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestPlanDesarrollo:

    @pytest.fixture
    def plan(self, personal, ciclo):
        return PlanDesarrollo.objects.create(
            personal=personal,
            ciclo=ciclo,
            titulo='Desarrollar liderazgo de equipo',
            objetivo='Mejorar capacidad de delegación y seguimiento.',
            fecha_inicio=date(2026, 2, 1),
            fecha_fin=date(2026, 6, 30),
        )

    def test_crear_plan(self, plan):
        assert plan.estado == 'BORRADOR'
        assert 'FERNANDEZ DIAZ MARIA' in str(plan)

    def test_porcentaje_avance_sin_acciones(self, plan):
        assert plan.porcentaje_avance == 0

    def test_porcentaje_avance_parcial(self, plan):
        AccionDesarrollo.objects.create(
            plan=plan, descripcion='Curso liderazgo',
            fecha_limite=date(2026, 3, 15), completada=True,
        )
        AccionDesarrollo.objects.create(
            plan=plan, descripcion='Proyecto mentoria',
            tipo='MENTORIA',
            fecha_limite=date(2026, 5, 1), completada=False,
        )
        assert plan.porcentaje_avance == 50

    def test_porcentaje_avance_completo(self, plan):
        AccionDesarrollo.objects.create(
            plan=plan, descripcion='Accion 1',
            fecha_limite=date(2026, 3, 15), completada=True,
        )
        AccionDesarrollo.objects.create(
            plan=plan, descripcion='Accion 2',
            fecha_limite=date(2026, 4, 15), completada=True,
        )
        assert plan.porcentaje_avance == 100


# ──────────────────────────────────────────────────────────────
# OKR — ObjetivoClave y ResultadoClave
# ──────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestOKR:

    @pytest.fixture
    def objetivo(self, personal):
        return ObjetivoClave.objects.create(
            titulo='Reducir rotación de personal al 5%',
            nivel='INDIVIDUAL',
            personal=personal,
            periodo='TRIMESTRAL',
            anio=2026,
            trimestre=1,
            status='ACTIVO',
        )

    @pytest.fixture
    def kr_porcentaje(self, objetivo):
        return ResultadoClave.objects.create(
            objetivo=objetivo,
            descripcion='Reducir rotación de 10% a 5%',
            unidad='PORCENTAJE',
            valor_inicial=Decimal('10.00'),
            valor_meta=Decimal('5.00'),
            valor_actual=Decimal('7.00'),
            orden=1,
        )

    def test_crear_objetivo(self, objetivo):
        assert objetivo.status == 'ACTIVO'
        assert str(objetivo) == 'Reducir rotación de personal al 5%'

    def test_periodo_display_trimestral(self, objetivo):
        assert objetivo.periodo_display == 'Q1 2026'

    def test_periodo_display_anual(self, personal):
        obj = ObjetivoClave.objects.create(
            titulo='Objetivo anual', nivel='EMPRESA',
            periodo='ANUAL', anio=2026,
        )
        assert obj.periodo_display == '2026'

    def test_color_status(self, objetivo):
        assert objetivo.color_status == 'primary'
        objetivo.status = 'EN_RIESGO'
        assert objetivo.color_status == 'warning'
        objetivo.status = 'COMPLETADO'
        assert objetivo.color_status == 'success'

    def test_avance_promedio_sin_krs(self, objetivo):
        assert objetivo.avance_promedio == 0

    def test_kr_porcentaje_avance(self, kr_porcentaje):
        """
        Rango: 10 -> 5 (rango = -5, es decreciente)
        Actual: 7, avance = (7-10) / (5-10) * 100 = (-3/-5)*100 = 60%
        """
        assert kr_porcentaje.porcentaje_avance == 60

    def test_kr_si_no(self, objetivo):
        kr = ResultadoClave.objects.create(
            objetivo=objetivo,
            descripcion='Implementar sistema de encuestas',
            unidad='SI_NO',
            valor_meta=Decimal('1.00'),
            completado_binario=False,
        )
        assert kr.porcentaje_avance == 0
        kr.completado_binario = True
        assert kr.porcentaje_avance == 100

    def test_kr_meta_alcanzada(self, objetivo):
        kr = ResultadoClave.objects.create(
            objetivo=objetivo,
            descripcion='Capacitar 50 personas',
            unidad='NUMERO',
            valor_inicial=Decimal('0.00'),
            valor_meta=Decimal('50.00'),
            valor_actual=Decimal('60.00'),  # Excede meta
        )
        # Debe limitarse a 100%
        assert kr.porcentaje_avance == 100

    def test_kr_color_avance(self, objetivo):
        kr = ResultadoClave.objects.create(
            objetivo=objetivo,
            descripcion='Test avance',
            unidad='NUMERO',
            valor_inicial=Decimal('0.00'),
            valor_meta=Decimal('100.00'),
            valor_actual=Decimal('75.00'),
        )
        assert kr.color_avance == 'success'

        kr.valor_actual = Decimal('45.00')
        assert kr.color_avance == 'warning'

        kr.valor_actual = Decimal('10.00')
        assert kr.color_avance == 'danger'

    def test_kr_unidad_label(self, objetivo):
        kr = ResultadoClave.objects.create(
            objetivo=objetivo,
            descripcion='Test', unidad='PORCENTAJE',
            valor_meta=Decimal('100.00'),
        )
        assert kr.unidad_label == '%'

    def test_kr_unidad_personalizada(self, objetivo):
        kr = ResultadoClave.objects.create(
            objetivo=objetivo,
            descripcion='Test', unidad='PERSONALIZADO',
            unidad_personalizada='tickets',
            valor_meta=Decimal('100.00'),
        )
        assert kr.unidad_label == 'tickets'

    def test_avance_promedio_con_krs(self, objetivo):
        ResultadoClave.objects.create(
            objetivo=objetivo, descripcion='KR1',
            unidad='PORCENTAJE',
            valor_inicial=Decimal('0.00'),
            valor_meta=Decimal('100.00'),
            valor_actual=Decimal('50.00'),  # 50%
        )
        ResultadoClave.objects.create(
            objetivo=objetivo, descripcion='KR2',
            unidad='SI_NO',
            valor_meta=Decimal('1.00'),
            completado_binario=True,  # 100%
        )
        # Promedio: (50 + 100) / 2 = 75
        assert objetivo.avance_promedio == 75

    def test_objetivo_cascada(self, personal):
        """Objetivo de empresa puede tener hijos de area."""
        padre = ObjetivoClave.objects.create(
            titulo='Objetivo Empresa', nivel='EMPRESA',
            periodo='ANUAL', anio=2026,
        )
        hijo = ObjetivoClave.objects.create(
            titulo='Objetivo Área', nivel='AREA',
            periodo='TRIMESTRAL', anio=2026, trimestre=1,
            objetivo_padre=padre,
        )
        assert hijo.objetivo_padre == padre
        assert padre.objetivos_hijo.count() == 1


@pytest.mark.django_db
class TestCheckInOKR:

    def test_crear_checkin(self, user):
        objetivo = ObjetivoClave.objects.create(
            titulo='OKR Test', nivel='EMPRESA',
            periodo='TRIMESTRAL', anio=2026, trimestre=1,
        )
        kr = ResultadoClave.objects.create(
            objetivo=objetivo, descripcion='KR test',
            unidad='NUMERO', valor_meta=Decimal('100.00'),
        )
        checkin = CheckInOKR.objects.create(
            resultado_clave=kr,
            fecha=date(2026, 2, 15),
            valor_nuevo=Decimal('35.00'),
            comentario='Avance en Q1, sin bloqueos.',
            registrado_por=user,
        )
        assert 'KR test' in str(checkin)
        assert checkin.valor_nuevo == Decimal('35.00')
