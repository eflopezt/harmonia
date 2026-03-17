"""
Tests para modelos del modulo cierre (Cierre Mensual).
Valida estados, wizard de pasos, propiedades de avance y transiciones.
"""
import pytest
from django.utils import timezone
from cierre.models import PeriodoCierre, PasoCierre


@pytest.fixture
def periodo():
    return PeriodoCierre.objects.create(anio=2026, mes=3)


@pytest.fixture
def periodo_con_pasos(periodo):
    """Periodo con 3 pasos: 2 OK, 1 PENDIENTE."""
    PasoCierre.objects.create(
        periodo=periodo, codigo='VERIFICAR_IMPORTACIONES', orden=1, estado='OK',
    )
    PasoCierre.objects.create(
        periodo=periodo, codigo='VALIDAR_DNI', orden=2, estado='OK',
    )
    PasoCierre.objects.create(
        periodo=periodo, codigo='BLOQUEAR_PERIODO', orden=3, estado='PENDIENTE',
    )
    return periodo


# ──────────────────────────────────────────────────────────────
# PeriodoCierre
# ──────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestPeriodoCierre:

    def test_crear_periodo_defaults(self, periodo):
        assert periodo.estado == 'ABIERTO'
        assert periodo.cerrado_en is None
        assert periodo.notas == ''

    def test_str_formato(self, periodo):
        """__str__ debe mostrar 'Mar 2026 [Abierto ...]'."""
        s = str(periodo)
        assert 'Mar' in s
        assert '2026' in s

    def test_mes_nombre_property(self, periodo):
        assert periodo.mes_nombre == 'Marzo'

    def test_mes_nombre_enero(self):
        p = PeriodoCierre.objects.create(anio=2026, mes=1)
        assert p.mes_nombre == 'Enero'

    def test_mes_nombre_diciembre(self):
        p = PeriodoCierre.objects.create(anio=2025, mes=12)
        assert p.mes_nombre == 'Diciembre'

    def test_esta_cerrado_false_cuando_abierto(self, periodo):
        assert periodo.esta_cerrado is False

    def test_esta_cerrado_true(self, periodo):
        periodo.estado = 'CERRADO'
        periodo.save()
        assert periodo.esta_cerrado is True

    def test_unique_together_anio_mes(self, periodo):
        from django.db import IntegrityError
        with pytest.raises(IntegrityError):
            PeriodoCierre.objects.create(anio=2026, mes=3)

    def test_porcentaje_avance_sin_pasos(self, periodo):
        assert periodo.porcentaje_avance == 0

    def test_porcentaje_avance_con_pasos(self, periodo_con_pasos):
        # 2 de 3 completados = 67%
        assert periodo_con_pasos.pasos_completados == 2
        assert periodo_con_pasos.total_pasos == 3
        assert periodo_con_pasos.porcentaje_avance == 67

    def test_porcentaje_avance_todos_ok(self, periodo):
        PasoCierre.objects.create(
            periodo=periodo, codigo='VERIFICAR_IMPORTACIONES', orden=1, estado='OK',
        )
        PasoCierre.objects.create(
            periodo=periodo, codigo='VALIDAR_DNI', orden=2, estado='OK',
        )
        assert periodo.porcentaje_avance == 100

    def test_ordering_descendente(self):
        p1 = PeriodoCierre.objects.create(anio=2025, mes=6)
        p2 = PeriodoCierre.objects.create(anio=2026, mes=1)
        p3 = PeriodoCierre.objects.create(anio=2026, mes=3)
        periodos = list(PeriodoCierre.objects.all())
        assert periodos[0] == p3  # 2026-03 primero
        assert periodos[1] == p2
        assert periodos[2] == p1


# ──────────────────────────────────────────────────────────────
# PasoCierre
# ──────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestPasoCierre:

    def test_crear_paso_defaults(self, periodo):
        paso = PasoCierre.objects.create(
            periodo=periodo, codigo='VERIFICAR_IMPORTACIONES', orden=1,
        )
        assert paso.estado == 'PENDIENTE'
        assert paso.resultado == {}
        assert paso.ejecutado_en is None

    def test_str_formato(self, periodo):
        paso = PasoCierre.objects.create(
            periodo=periodo, codigo='GENERAR_CARGA_S10', orden=5,
        )
        s = str(paso)
        assert 'Paso 5' in s
        assert 'Generar Carga S10 para RCO' in s

    def test_icono_por_estado(self, periodo):
        paso = PasoCierre.objects.create(
            periodo=periodo, codigo='VERIFICAR_IMPORTACIONES', orden=1,
        )
        paso.estado = 'OK'
        assert 'check-circle' in paso.icono
        assert 'success' in paso.icono

        paso.estado = 'ERROR'
        assert 'times-circle' in paso.icono
        assert 'danger' in paso.icono

        paso.estado = 'PENDIENTE'
        assert 'text-muted' in paso.icono

    def test_badge_class_por_estado(self, periodo):
        paso = PasoCierre.objects.create(
            periodo=periodo, codigo='VERIFICAR_IMPORTACIONES', orden=1,
        )
        paso.estado = 'OK'
        assert paso.badge_class == 'bg-success'

        paso.estado = 'ERROR'
        assert paso.badge_class == 'bg-danger'

        paso.estado = 'EJECUTANDO'
        assert paso.badge_class == 'bg-warning text-dark'

    def test_unique_together_periodo_codigo(self, periodo):
        from django.db import IntegrityError
        PasoCierre.objects.create(
            periodo=periodo, codigo='VERIFICAR_IMPORTACIONES', orden=1,
        )
        with pytest.raises(IntegrityError):
            PasoCierre.objects.create(
                periodo=periodo, codigo='VERIFICAR_IMPORTACIONES', orden=2,
            )

    def test_ordering_por_orden(self, periodo):
        p3 = PasoCierre.objects.create(
            periodo=periodo, codigo='BLOQUEAR_PERIODO', orden=3,
        )
        p1 = PasoCierre.objects.create(
            periodo=periodo, codigo='VERIFICAR_IMPORTACIONES', orden=1,
        )
        p2 = PasoCierre.objects.create(
            periodo=periodo, codigo='VALIDAR_DNI', orden=2,
        )
        pasos = list(periodo.pasos.all())
        assert pasos == [p1, p2, p3]

    def test_resultado_json_field(self, periodo):
        paso = PasoCierre.objects.create(
            periodo=periodo, codigo='VERIFICAR_IMPORTACIONES', orden=1,
            resultado={'registros_ok': 150, 'errores': 2},
        )
        paso.refresh_from_db()
        assert paso.resultado['registros_ok'] == 150
        assert paso.resultado['errores'] == 2

    def test_transicion_estados(self, periodo):
        """Simula la transicion PENDIENTE -> EJECUTANDO -> OK."""
        paso = PasoCierre.objects.create(
            periodo=periodo, codigo='VERIFICAR_IMPORTACIONES', orden=1,
        )
        assert paso.estado == 'PENDIENTE'

        paso.estado = 'EJECUTANDO'
        paso.save()
        assert paso.estado == 'EJECUTANDO'

        paso.estado = 'OK'
        paso.ejecutado_en = timezone.now()
        paso.save()
        assert paso.estado == 'OK'
        assert paso.ejecutado_en is not None
