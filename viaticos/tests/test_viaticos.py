"""
Tests para modelos del modulo viaticos.
Valida conceptos, asignaciones, gastos, conciliacion y topes diarios.
Legislacion: Art. 37 LIR Peru.
"""
import pytest
from datetime import date, timedelta
from decimal import Decimal
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

from personal.models import Area, SubArea, Personal
from viaticos.models import ConceptoViatico, AsignacionViatico, GastoViatico


@pytest.fixture
def area():
    return Area.objects.create(nombre='OPERACIONES CAMPO')


@pytest.fixture
def personal(area):
    subarea = SubArea.objects.create(nombre='MINA', area=area)
    return Personal.objects.create(
        nro_doc='22222222',
        apellidos_nombres='QUISPE HUAMAN PEDRO',
        cargo='Operador de Maquinaria',
        tipo_trab='Obrero',
        subarea=subarea,
        estado='Activo',
    )


@pytest.fixture
def user():
    return User.objects.create_user(username='admin_viaticos', password='test1234')


@pytest.fixture
def concepto_alimentacion():
    return ConceptoViatico.objects.create(
        nombre='Alimentación',
        codigo='alimentacion',
        tope_diario=Decimal('93.00'),  # Tope diario SUNAT zona nacional
        requiere_comprobante=True,
        afecto_renta=True,
    )


@pytest.fixture
def concepto_movilidad():
    return ConceptoViatico.objects.create(
        nombre='Movilidad Local',
        codigo='movilidad-local',
        tope_diario=None,  # Sin tope
        requiere_comprobante=False,
    )


@pytest.fixture
def asignacion(personal, user):
    return AsignacionViatico.objects.create(
        personal=personal,
        periodo=date(2026, 3, 1),
        monto_asignado=Decimal('2500.00'),
        monto_adicional=Decimal('0.00'),
        ubicacion='Proyecto Minero Quellaveco',
        dias_campo=20,
        creado_por=user,
    )


# ──────────────────────────────────────────────────────────────
# ConceptoViatico
# ──────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestConceptoViatico:

    def test_crear_concepto(self, concepto_alimentacion):
        assert concepto_alimentacion.tope_diario == Decimal('93.00')
        assert concepto_alimentacion.requiere_comprobante is True
        assert concepto_alimentacion.afecto_renta is True
        assert concepto_alimentacion.activo is True

    def test_str(self, concepto_alimentacion):
        assert str(concepto_alimentacion) == 'Alimentación'

    def test_concepto_sin_tope(self, concepto_movilidad):
        assert concepto_movilidad.tope_diario is None

    def test_nombre_unique(self, concepto_alimentacion):
        from django.db import IntegrityError
        with pytest.raises(IntegrityError):
            ConceptoViatico.objects.create(
                nombre='Alimentación', codigo='alimentacion-2',
            )

    def test_codigo_unique(self, concepto_alimentacion):
        from django.db import IntegrityError
        with pytest.raises(IntegrityError):
            ConceptoViatico.objects.create(
                nombre='Alimentación 2', codigo='alimentacion',
            )


# ──────────────────────────────────────────────────────────────
# AsignacionViatico
# ──────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestAsignacionViatico:

    def test_crear_asignacion_defaults(self, asignacion):
        assert asignacion.estado == 'BORRADOR'
        assert asignacion.monto_rendido == Decimal('0.00')
        assert asignacion.monto_devuelto == Decimal('0.00')
        assert asignacion.monto_reembolso == Decimal('0.00')

    def test_str(self, asignacion):
        s = str(asignacion)
        assert 'QUISPE HUAMAN PEDRO' in s
        assert '03/2026' in s

    def test_monto_total_sin_adicional(self, asignacion):
        assert asignacion.monto_total == Decimal('2500.00')

    def test_monto_total_con_adicional(self, asignacion):
        asignacion.monto_adicional = Decimal('300.00')
        asignacion.save()
        assert asignacion.monto_total == Decimal('2800.00')

    def test_saldo_sin_rendicion(self, asignacion):
        # rendido (0) - total (2500) = -2500 (sobra dinero)
        assert asignacion.saldo == Decimal('-2500.00')

    def test_saldo_con_rendicion_exacta(self, asignacion):
        asignacion.monto_rendido = Decimal('2500.00')
        assert asignacion.saldo == Decimal('0.00')

    def test_estado_conciliacion_cuadrado(self, asignacion):
        asignacion.monto_rendido = Decimal('2500.00')
        assert asignacion.estado_conciliacion == 'CUADRADO'

    def test_estado_conciliacion_reembolsar(self, asignacion):
        """Trabajador gasto mas de lo asignado, empresa debe reembolsar."""
        asignacion.monto_rendido = Decimal('2800.00')
        assert asignacion.estado_conciliacion == 'REEMBOLSAR'

    def test_estado_conciliacion_devolver(self, asignacion):
        """Trabajador gasto menos, debe devolver el saldo."""
        asignacion.monto_rendido = Decimal('2000.00')
        assert asignacion.estado_conciliacion == 'DEVOLVER'

    def test_aprobar(self, asignacion, user):
        asignacion.aprobar(user)
        asignacion.refresh_from_db()
        assert asignacion.estado == 'APROBADO'
        assert asignacion.aprobado_por == user

    def test_entregar(self, asignacion):
        asignacion.entregar()
        asignacion.refresh_from_db()
        assert asignacion.estado == 'ENTREGADO'
        assert asignacion.fecha_entrega == date.today()

    def test_entregar_con_fecha_especifica(self, asignacion):
        fecha = date(2026, 3, 5)
        asignacion.entregar(fecha=fecha)
        asignacion.refresh_from_db()
        assert asignacion.fecha_entrega == fecha

    def test_unique_together_personal_periodo(self, personal, user):
        AsignacionViatico.objects.create(
            personal=personal, periodo=date(2026, 4, 1),
            monto_asignado=Decimal('1000.00'),
        )
        from django.db import IntegrityError
        with pytest.raises(IntegrityError):
            AsignacionViatico.objects.create(
                personal=personal, periodo=date(2026, 4, 1),
                monto_asignado=Decimal('2000.00'),
            )

    def test_monto_asignado_minimo(self):
        """monto_asignado debe ser al menos 1.00."""
        a = AsignacionViatico(monto_asignado=Decimal('0.50'))
        # Validators se evaluan en full_clean
        with pytest.raises(ValidationError):
            a.full_clean()

    def test_conciliar_sin_gastos(self, asignacion):
        """Conciliar sin gastos aprobados: monto_rendido=0, debe devolver todo."""
        asignacion.conciliar()
        asignacion.refresh_from_db()
        assert asignacion.estado == 'CONCILIADO'
        assert asignacion.monto_rendido == Decimal('0.00')
        assert asignacion.monto_devuelto == Decimal('2500.00')
        assert asignacion.monto_reembolso == Decimal('0.00')

    def test_conciliar_con_gastos_aprobados(self, asignacion, concepto_alimentacion):
        """Conciliar con gastos parcialmente aprobados."""
        GastoViatico.objects.create(
            asignacion=asignacion, concepto=concepto_alimentacion,
            fecha_gasto=date(2026, 3, 10), monto=Decimal('80.00'),
            estado='APROBADO',
        )
        GastoViatico.objects.create(
            asignacion=asignacion, concepto=concepto_alimentacion,
            fecha_gasto=date(2026, 3, 11), monto=Decimal('90.00'),
            estado='APROBADO',
        )
        GastoViatico.objects.create(
            asignacion=asignacion, concepto=concepto_alimentacion,
            fecha_gasto=date(2026, 3, 12), monto=Decimal('50.00'),
            estado='RECHAZADO',  # No debe contar
        )
        asignacion.conciliar()
        asignacion.refresh_from_db()

        assert asignacion.monto_rendido == Decimal('170.00')
        assert asignacion.estado == 'CONCILIADO'
        # 170 - 2500 = -2330 (trabajador debe devolver)
        assert asignacion.monto_devuelto == Decimal('2330.00')
        assert asignacion.monto_reembolso == Decimal('0.00')

    def test_conciliar_con_exceso(self, asignacion, concepto_alimentacion):
        """Cuando trabajador gasto mas de lo asignado, empresa reembolsa."""
        GastoViatico.objects.create(
            asignacion=asignacion, concepto=concepto_alimentacion,
            fecha_gasto=date(2026, 3, 10), monto=Decimal('2700.00'),
            estado='APROBADO',
        )
        asignacion.conciliar()
        asignacion.refresh_from_db()

        assert asignacion.monto_rendido == Decimal('2700.00')
        assert asignacion.monto_reembolso == Decimal('200.00')
        assert asignacion.monto_devuelto == Decimal('0.00')


# ──────────────────────────────────────────────────────────────
# GastoViatico
# ──────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestGastoViatico:

    def test_crear_gasto(self, asignacion, concepto_alimentacion):
        gasto = GastoViatico.objects.create(
            asignacion=asignacion,
            concepto=concepto_alimentacion,
            fecha_gasto=date(2026, 3, 10),
            monto=Decimal('85.00'),
            tipo_comprobante='BOLETA',
            numero_comprobante='B001-00123',
            ruc_proveedor='20123456789',
        )
        assert gasto.estado == 'PENDIENTE'
        assert 'Alimentación' in str(gasto)
        assert '85.00' in str(gasto)

    def test_excede_tope_false(self, asignacion, concepto_alimentacion):
        """Gasto dentro del tope diario (93.00)."""
        gasto = GastoViatico.objects.create(
            asignacion=asignacion, concepto=concepto_alimentacion,
            fecha_gasto=date(2026, 3, 10), monto=Decimal('80.00'),
        )
        assert gasto.excede_tope is False

    def test_excede_tope_true(self, asignacion, concepto_alimentacion):
        """Gasto que excede el tope diario SUNAT."""
        gasto = GastoViatico.objects.create(
            asignacion=asignacion, concepto=concepto_alimentacion,
            fecha_gasto=date(2026, 3, 10), monto=Decimal('150.00'),
        )
        assert gasto.excede_tope is True

    def test_monto_exceso_calculo(self, asignacion, concepto_alimentacion):
        """Tope = 93.00, gasto = 150.00, exceso = 57.00."""
        gasto = GastoViatico.objects.create(
            asignacion=asignacion, concepto=concepto_alimentacion,
            fecha_gasto=date(2026, 3, 10), monto=Decimal('150.00'),
        )
        assert gasto.monto_exceso == Decimal('57.00')

    def test_monto_exceso_sin_tope(self, asignacion, concepto_movilidad):
        """Concepto sin tope: exceso siempre 0."""
        gasto = GastoViatico.objects.create(
            asignacion=asignacion, concepto=concepto_movilidad,
            fecha_gasto=date(2026, 3, 10), monto=Decimal('500.00'),
        )
        assert gasto.excede_tope is False
        assert gasto.monto_exceso == Decimal('0.00')

    def test_monto_exceso_exacto_en_tope(self, asignacion, concepto_alimentacion):
        """Gasto exactamente en el tope: no excede."""
        gasto = GastoViatico.objects.create(
            asignacion=asignacion, concepto=concepto_alimentacion,
            fecha_gasto=date(2026, 3, 10), monto=Decimal('93.00'),
        )
        assert gasto.excede_tope is False
        assert gasto.monto_exceso == Decimal('0.00')

    def test_monto_minimo_validacion(self, asignacion, concepto_alimentacion):
        """monto debe ser al menos 0.01."""
        gasto = GastoViatico(
            asignacion=asignacion, concepto=concepto_alimentacion,
            fecha_gasto=date(2026, 3, 10), monto=Decimal('0.00'),
        )
        with pytest.raises(ValidationError):
            gasto.full_clean()
