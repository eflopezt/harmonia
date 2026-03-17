"""
Tests para modelos del modulo onboarding / offboarding.
Valida plantillas, procesos, pasos, avance y vencimientos.
"""
import pytest
from datetime import date, timedelta
from django.utils import timezone
from django.contrib.auth.models import User

from personal.models import Area, SubArea, Personal
from onboarding.models import (
    PlantillaOnboarding, PasoPlantilla,
    ProcesoOnboarding, PasoOnboarding,
    PlantillaOffboarding, PasoPlantillaOff,
    ProcesoOffboarding, PasoOffboarding,
)


@pytest.fixture
def area():
    return Area.objects.create(nombre='OPERACIONES')


@pytest.fixture
def personal(area):
    subarea = SubArea.objects.create(nombre='CAMPO', area=area)
    return Personal.objects.create(
        nro_doc='11111111',
        apellidos_nombres='GARCIA LOPEZ JUAN',
        cargo='Operario',
        tipo_trab='Obrero',
        subarea=subarea,
        estado='Activo',
    )


@pytest.fixture
def plantilla_onboarding():
    return PlantillaOnboarding.objects.create(
        nombre='Onboarding Estándar',
        aplica_grupo='TODOS',
    )


@pytest.fixture
def plantilla_con_pasos(plantilla_onboarding):
    PasoPlantilla.objects.create(
        plantilla=plantilla_onboarding, orden=1,
        titulo='Firmar contrato', tipo='DOCUMENTO',
        responsable_tipo='RRHH', dias_plazo=1,
    )
    PasoPlantilla.objects.create(
        plantilla=plantilla_onboarding, orden=2,
        titulo='Crear usuario en sistema', tipo='TAREA',
        responsable_tipo='TI', dias_plazo=2,
    )
    PasoPlantilla.objects.create(
        plantilla=plantilla_onboarding, orden=3,
        titulo='Induccion seguridad', tipo='CAPACITACION',
        responsable_tipo='JEFE', dias_plazo=5, obligatorio=True,
    )
    return plantilla_onboarding


@pytest.fixture
def proceso_onboarding(personal, plantilla_con_pasos):
    return ProcesoOnboarding.objects.create(
        personal=personal,
        plantilla=plantilla_con_pasos,
        fecha_ingreso=date.today(),
        fecha_inicio=date.today(),
    )


# ──────────────────────────────────────────────────────────────
# PlantillaOnboarding
# ──────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestPlantillaOnboarding:

    def test_crear_plantilla_defaults(self, plantilla_onboarding):
        assert plantilla_onboarding.activa is True
        assert plantilla_onboarding.aplica_grupo == 'TODOS'

    def test_str(self, plantilla_onboarding):
        assert str(plantilla_onboarding) == 'Onboarding Estándar'

    def test_total_pasos_sin_pasos(self, plantilla_onboarding):
        assert plantilla_onboarding.total_pasos == 0

    def test_total_pasos_con_pasos(self, plantilla_con_pasos):
        assert plantilla_con_pasos.total_pasos == 3

    def test_nombre_unique(self, plantilla_onboarding):
        from django.db import IntegrityError
        with pytest.raises(IntegrityError):
            PlantillaOnboarding.objects.create(nombre='Onboarding Estándar')

    def test_aplica_areas_m2m(self, plantilla_onboarding, area):
        plantilla_onboarding.aplica_areas.add(area)
        assert area in plantilla_onboarding.aplica_areas.all()


# ──────────────────────────────────────────────────────────────
# PasoPlantilla
# ──────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestPasoPlantilla:

    def test_str(self, plantilla_con_pasos):
        paso = plantilla_con_pasos.pasos.first()
        assert paso.orden == 1
        assert str(paso) == '1. Firmar contrato'

    def test_unique_together_plantilla_orden(self, plantilla_onboarding):
        PasoPlantilla.objects.create(
            plantilla=plantilla_onboarding, orden=1, titulo='Paso A',
        )
        from django.db import IntegrityError
        with pytest.raises(IntegrityError):
            PasoPlantilla.objects.create(
                plantilla=plantilla_onboarding, orden=1, titulo='Paso B',
            )

    def test_defaults(self, plantilla_onboarding):
        paso = PasoPlantilla.objects.create(
            plantilla=plantilla_onboarding, orden=1, titulo='Test',
        )
        assert paso.tipo == 'TAREA'
        assert paso.responsable_tipo == 'RRHH'
        assert paso.dias_plazo == 1
        assert paso.obligatorio is True


# ──────────────────────────────────────────────────────────────
# ProcesoOnboarding
# ──────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestProcesoOnboarding:

    def test_crear_proceso_defaults(self, proceso_onboarding):
        assert proceso_onboarding.estado == 'EN_CURSO'
        assert proceso_onboarding.notas == ''

    def test_str(self, proceso_onboarding):
        assert 'GARCIA LOPEZ JUAN' in str(proceso_onboarding)

    def test_porcentaje_avance_sin_pasos(self, proceso_onboarding):
        assert proceso_onboarding.porcentaje_avance == 0

    def test_porcentaje_avance_parcial(self, proceso_onboarding):
        PasoOnboarding.objects.create(
            proceso=proceso_onboarding, orden=1, titulo='Paso 1',
            estado='COMPLETADO',
        )
        PasoOnboarding.objects.create(
            proceso=proceso_onboarding, orden=2, titulo='Paso 2',
            estado='PENDIENTE',
        )
        assert proceso_onboarding.porcentaje_avance == 50

    def test_porcentaje_avance_completo(self, proceso_onboarding):
        PasoOnboarding.objects.create(
            proceso=proceso_onboarding, orden=1, titulo='Paso 1',
            estado='COMPLETADO',
        )
        assert proceso_onboarding.porcentaje_avance == 100

    def test_dias_transcurridos(self, proceso_onboarding):
        proceso_onboarding.fecha_inicio = date.today() - timedelta(days=5)
        proceso_onboarding.save()
        assert proceso_onboarding.dias_transcurridos == 5

    def test_total_pasos_y_completados(self, proceso_onboarding):
        PasoOnboarding.objects.create(
            proceso=proceso_onboarding, orden=1, titulo='A', estado='COMPLETADO',
        )
        PasoOnboarding.objects.create(
            proceso=proceso_onboarding, orden=2, titulo='B', estado='PENDIENTE',
        )
        PasoOnboarding.objects.create(
            proceso=proceso_onboarding, orden=3, titulo='C', estado='COMPLETADO',
        )
        assert proceso_onboarding.total_pasos == 3
        assert proceso_onboarding.pasos_completados == 2


# ──────────────────────────────────────────────────────────────
# PasoOnboarding
# ──────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestPasoOnboarding:

    def test_str(self, proceso_onboarding):
        paso = PasoOnboarding.objects.create(
            proceso=proceso_onboarding, orden=1, titulo='Firmar contrato',
        )
        assert '1. Firmar contrato' in str(paso)
        assert 'Pendiente' in str(paso)

    def test_esta_vencido_sin_fecha_limite(self, proceso_onboarding):
        paso = PasoOnboarding.objects.create(
            proceso=proceso_onboarding, orden=1, titulo='Test',
        )
        assert paso.esta_vencido is False

    def test_esta_vencido_con_fecha_futura(self, proceso_onboarding):
        paso = PasoOnboarding.objects.create(
            proceso=proceso_onboarding, orden=1, titulo='Test',
            fecha_limite=date.today() + timedelta(days=5),
        )
        assert paso.esta_vencido is False

    def test_esta_vencido_con_fecha_pasada(self, proceso_onboarding):
        paso = PasoOnboarding.objects.create(
            proceso=proceso_onboarding, orden=1, titulo='Test',
            fecha_limite=date.today() - timedelta(days=1),
        )
        assert paso.esta_vencido is True

    def test_no_vencido_si_completado(self, proceso_onboarding):
        """Un paso completado nunca esta vencido, incluso con fecha pasada."""
        paso = PasoOnboarding.objects.create(
            proceso=proceso_onboarding, orden=1, titulo='Test',
            estado='COMPLETADO',
            fecha_limite=date.today() - timedelta(days=10),
        )
        assert paso.esta_vencido is False

    def test_no_vencido_si_omitido(self, proceso_onboarding):
        paso = PasoOnboarding.objects.create(
            proceso=proceso_onboarding, orden=1, titulo='Test',
            estado='OMITIDO',
            fecha_limite=date.today() - timedelta(days=10),
        )
        assert paso.esta_vencido is False


# ──────────────────────────────────────────────────────────────
# Offboarding
# ──────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestProcesoOffboarding:

    @pytest.fixture
    def plantilla_off(self):
        return PlantillaOffboarding.objects.create(nombre='Offboarding Estándar')

    @pytest.fixture
    def proceso_off(self, personal, plantilla_off):
        return ProcesoOffboarding.objects.create(
            personal=personal,
            plantilla=plantilla_off,
            fecha_cese=date.today() + timedelta(days=15),
            motivo_cese='RENUNCIA',
        )

    def test_crear_offboarding(self, proceso_off):
        assert proceso_off.estado == 'EN_CURSO'
        assert proceso_off.motivo_cese == 'RENUNCIA'
        assert 'GARCIA LOPEZ JUAN' in str(proceso_off)

    def test_porcentaje_avance_offboarding(self, proceso_off):
        PasoOffboarding.objects.create(
            proceso=proceso_off, orden=1, titulo='Devolver equipos',
            estado='COMPLETADO',
        )
        PasoOffboarding.objects.create(
            proceso=proceso_off, orden=2, titulo='Liquidación',
            estado='PENDIENTE',
        )
        assert proceso_off.porcentaje_avance == 50

    def test_plantilla_off_total_pasos(self, plantilla_off):
        assert plantilla_off.total_pasos == 0
        PasoPlantillaOff.objects.create(
            plantilla=plantilla_off, orden=1, titulo='Paso Off 1',
        )
        assert plantilla_off.total_pasos == 1

    def test_paso_offboarding_esta_vencido(self, proceso_off):
        paso = PasoOffboarding.objects.create(
            proceso=proceso_off, orden=1, titulo='Test',
            fecha_limite=date.today() - timedelta(days=3),
        )
        assert paso.esta_vencido is True

    def test_motivos_cese_validos(self, proceso_off):
        motivos_validos = ['RENUNCIA', 'DESPIDO', 'MUTUO_ACUERDO',
                           'FIN_CONTRATO', 'JUBILACION']
        assert proceso_off.motivo_cese in motivos_validos
