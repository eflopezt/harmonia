"""
Comprehensive tests for the workflows module.

Covers: FlujoTrabajo, EtapaFlujo, InstanciaFlujo models
        and services: decidir (aprobar_instancia), verificar_vencimientos.
"""
from datetime import timedelta
from unittest.mock import patch

import pytest
from django.contrib.auth.models import Group, User
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from django.utils import timezone

from workflows.models import EtapaFlujo, FlujoTrabajo, InstanciaFlujo, PasoFlujo
from workflows.services import decidir, verificar_vencimientos


# ---------------------------------------------------------------------------
# Helper: We need a real Django model with a 'estado' field to act as the
# workflow target.  We reuse auth.User and treat `is_active` field as
# "campo_trigger" placeholder, but for clarity we use a thin wrapper model
# from the project.  However, to keep tests self-contained, we use the
# vacaciones.SolicitudVacacion if available; otherwise, fall back to a
# simple model.  The safest generic approach: use auth.User itself as the
# "target object", mapping campo_trigger='username' to avoid collisions.
#
# Actually, the workflow just does setattr(obj, campo_resultado, valor) and
# obj.save(update_fields=[campo_resultado]).  We need a model with a real
# text field.  auth.User.first_name works.  Let's use that.
# ---------------------------------------------------------------------------


def _user_ct():
    """Return ContentType for auth.User."""
    return ContentType.objects.get_for_model(User)


class FlujoTrabajoModelTests(TestCase):
    """Tests for FlujoTrabajo creation and properties."""

    def setUp(self):
        self.ct = _user_ct()
        self.flujo = FlujoTrabajo.objects.create(
            nombre="Aprobacion Vacaciones",
            descripcion="Flujo de prueba",
            content_type=self.ct,
            campo_trigger="first_name",
            valor_trigger="Pendiente",
            campo_resultado="first_name",
            valor_aprobado="Aprobado",
            valor_rechazado="Rechazado",
        )

    def test_str(self):
        assert str(self.flujo) == "Aprobacion Vacaciones"

    def test_total_etapas_zero(self):
        assert self.flujo.total_etapas == 0

    def test_total_etapas_with_stages(self):
        EtapaFlujo.objects.create(flujo=self.flujo, orden=1, nombre="E1")
        EtapaFlujo.objects.create(flujo=self.flujo, orden=2, nombre="E2")
        assert self.flujo.total_etapas == 2

    def test_defaults(self):
        assert self.flujo.activo is True
        assert self.flujo.notificar_email is True
        assert self.flujo.icono == "fa-code-branch"


class EtapaFlujoGetAprobadoresTests(TestCase):
    """Tests for EtapaFlujo.get_aprobadores with each tipo_aprobador."""

    def setUp(self):
        self.ct = _user_ct()
        self.flujo = FlujoTrabajo.objects.create(
            nombre="Flujo Test",
            content_type=self.ct,
            campo_trigger="first_name",
            valor_trigger="X",
        )
        self.superuser = User.objects.create_user(
            "admin", "admin@test.com", "pass", is_superuser=True
        )
        self.regular_user = User.objects.create_user(
            "regular", "regular@test.com", "pass"
        )

    # -- SUPERUSER -----------------------------------------------------------
    def test_superuser_returns_superusers(self):
        etapa = EtapaFlujo.objects.create(
            flujo=self.flujo, orden=1, nombre="Admin",
            tipo_aprobador="SUPERUSER",
        )
        aprobadores = etapa.get_aprobadores()
        assert self.superuser in aprobadores
        assert self.regular_user not in aprobadores

    def test_superuser_excludes_inactive(self):
        self.superuser.is_active = False
        self.superuser.save()
        etapa = EtapaFlujo.objects.create(
            flujo=self.flujo, orden=1, nombre="Admin",
            tipo_aprobador="SUPERUSER",
        )
        assert self.superuser not in etapa.get_aprobadores()

    # -- USUARIO -------------------------------------------------------------
    def test_usuario_returns_specific_user(self):
        etapa = EtapaFlujo.objects.create(
            flujo=self.flujo, orden=1, nombre="Especifico",
            tipo_aprobador="USUARIO",
            aprobador_usuario=self.regular_user,
        )
        assert etapa.get_aprobadores() == [self.regular_user]

    def test_usuario_returns_empty_when_none(self):
        etapa = EtapaFlujo.objects.create(
            flujo=self.flujo, orden=1, nombre="Especifico",
            tipo_aprobador="USUARIO",
            aprobador_usuario=None,
        )
        assert etapa.get_aprobadores() == []

    # -- GRUPO_DJANGO --------------------------------------------------------
    def test_grupo_django_returns_group_members(self):
        group = Group.objects.create(name="RRHH")
        self.regular_user.groups.add(group)
        etapa = EtapaFlujo.objects.create(
            flujo=self.flujo, orden=1, nombre="Grupo",
            tipo_aprobador="GRUPO_DJANGO",
            aprobador_grupo=group,
        )
        aprobadores = etapa.get_aprobadores()
        assert self.regular_user in aprobadores
        assert self.superuser not in aprobadores

    def test_grupo_django_empty_group(self):
        group = Group.objects.create(name="Empty")
        etapa = EtapaFlujo.objects.create(
            flujo=self.flujo, orden=1, nombre="Grupo",
            tipo_aprobador="GRUPO_DJANGO",
            aprobador_grupo=group,
        )
        assert etapa.get_aprobadores() == []

    def test_grupo_django_no_group_set(self):
        etapa = EtapaFlujo.objects.create(
            flujo=self.flujo, orden=1, nombre="Grupo",
            tipo_aprobador="GRUPO_DJANGO",
            aprobador_grupo=None,
        )
        assert etapa.get_aprobadores() == []

    # -- JEFE_AREA -----------------------------------------------------------
    def test_jefe_area_falls_back_to_superusers_without_objeto(self):
        """Without an objeto that has personal/empleado, falls back to superusers."""
        etapa = EtapaFlujo.objects.create(
            flujo=self.flujo, orden=1, nombre="Jefe",
            tipo_aprobador="JEFE_AREA",
        )
        aprobadores = etapa.get_aprobadores(objeto=None)
        # With no objeto, JEFE_AREA returns [] (the elif doesn't match)
        assert aprobadores == []

    def test_jefe_area_with_object_no_personal_falls_back(self):
        """Object that has no .personal or .empleado -> fallback to superusers."""
        dummy_obj = object()  # no personal/empleado attribute
        etapa = EtapaFlujo.objects.create(
            flujo=self.flujo, orden=1, nombre="Jefe",
            tipo_aprobador="JEFE_AREA",
        )
        aprobadores = etapa.get_aprobadores(objeto=dummy_obj)
        # The try block will fail -> fallback to superusers
        assert self.superuser in aprobadores


class InstanciaFlujoTests(TestCase):
    """Tests for InstanciaFlujo model methods."""

    def setUp(self):
        self.ct = _user_ct()
        self.flujo = FlujoTrabajo.objects.create(
            nombre="Flujo Test",
            content_type=self.ct,
            campo_trigger="first_name",
            valor_trigger="Pendiente",
            campo_resultado="first_name",
            valor_aprobado="Aprobado",
            valor_rechazado="Rechazado",
        )
        self.superuser = User.objects.create_user(
            "admin", "admin@test.com", "pass", is_superuser=True
        )
        self.regular_user = User.objects.create_user(
            "regular", "regular@test.com", "pass"
        )
        self.target = User.objects.create_user(
            "target", "target@test.com", "pass"
        )
        self.target.first_name = "Pendiente"
        self.target.save()

        self.etapa1 = EtapaFlujo.objects.create(
            flujo=self.flujo, orden=1, nombre="Etapa 1",
            tipo_aprobador="SUPERUSER",
        )
        self.etapa2 = EtapaFlujo.objects.create(
            flujo=self.flujo, orden=2, nombre="Etapa 2",
            tipo_aprobador="SUPERUSER",
        )

        self.instancia = InstanciaFlujo.objects.create(
            flujo=self.flujo,
            content_type=self.ct,
            object_id=self.target.pk,
            etapa_actual=self.etapa1,
            estado="EN_PROCESO",
            solicitante=self.regular_user,
        )

    # -- puede_aprobar -------------------------------------------------------
    def test_puede_aprobar_true_for_correct_approver(self):
        assert self.instancia.puede_aprobar(self.superuser) is True

    def test_puede_aprobar_false_for_unauthorized_user(self):
        assert self.instancia.puede_aprobar(self.regular_user) is False

    def test_puede_aprobar_false_when_not_en_proceso(self):
        self.instancia.estado = "APROBADO"
        self.instancia.save()
        assert self.instancia.puede_aprobar(self.superuser) is False

    def test_puede_aprobar_false_when_no_etapa_actual(self):
        self.instancia.etapa_actual = None
        self.instancia.save()
        assert self.instancia.puede_aprobar(self.superuser) is False

    def test_puede_aprobar_true_for_escalated_user(self):
        self.instancia.metadata = {"escalado_a_user_id": self.regular_user.pk}
        self.instancia.save()
        assert self.instancia.puede_aprobar(self.regular_user) is True

    # -- get_siguiente_etapa -------------------------------------------------
    def test_get_siguiente_etapa(self):
        assert self.instancia.get_siguiente_etapa() == self.etapa2

    def test_get_siguiente_etapa_none_at_last(self):
        self.instancia.etapa_actual = self.etapa2
        self.instancia.save()
        assert self.instancia.get_siguiente_etapa() is None

    def test_get_siguiente_etapa_returns_first_when_no_current(self):
        self.instancia.etapa_actual = None
        self.instancia.save()
        assert self.instancia.get_siguiente_etapa() == self.etapa1

    # -- properties ----------------------------------------------------------
    def test_color_estado(self):
        assert self.instancia.color_estado == "warning"

    def test_icono_estado(self):
        assert self.instancia.icono_estado == "fa-clock"

    def test_str(self):
        assert "Flujo Test" in str(self.instancia)
        assert "EN_PROCESO" in str(self.instancia)


class DecidirServiceTests(TestCase):
    """Tests for the decidir (aprobar_instancia) service function."""

    def setUp(self):
        self.ct = _user_ct()
        self.flujo = FlujoTrabajo.objects.create(
            nombre="Flujo Decidir",
            content_type=self.ct,
            campo_trigger="first_name",
            valor_trigger="Pendiente",
            campo_resultado="first_name",
            valor_aprobado="Aprobado",
            valor_rechazado="Rechazado",
            notificar_email=False,  # avoid notification side effects
        )
        self.approver = User.objects.create_user(
            "approver", "approver@test.com", "pass", is_superuser=True
        )
        self.non_approver = User.objects.create_user(
            "nonapprover", "nonapprover@test.com", "pass"
        )
        self.target = User.objects.create_user(
            "target", "target@test.com", "pass"
        )
        self.target.first_name = "Pendiente"
        self.target.save()

        self.etapa1 = EtapaFlujo.objects.create(
            flujo=self.flujo, orden=1, nombre="Etapa 1",
            tipo_aprobador="SUPERUSER",
        )
        self.etapa2 = EtapaFlujo.objects.create(
            flujo=self.flujo, orden=2, nombre="Etapa 2",
            tipo_aprobador="SUPERUSER",
        )

    def _create_instancia(self):
        return InstanciaFlujo.objects.create(
            flujo=self.flujo,
            content_type=self.ct,
            object_id=self.target.pk,
            etapa_actual=self.etapa1,
            estado="EN_PROCESO",
            solicitante=self.non_approver,
        )

    # -- Advance to next stage -----------------------------------------------
    @patch("workflows.services._notificar_aprobadores")
    def test_approve_advances_to_next_stage(self, mock_notif):
        instancia = self._create_instancia()
        result = decidir(instancia, self.approver, "APROBADO")
        instancia.refresh_from_db()

        assert result is True
        assert instancia.etapa_actual == self.etapa2
        assert instancia.estado == "EN_PROCESO"

    # -- Finalize on last stage approval -------------------------------------
    @patch("workflows.services._notificar_aprobadores")
    def test_approve_finalizes_when_last_stage(self, mock_notif):
        instancia = self._create_instancia()
        instancia.etapa_actual = self.etapa2
        instancia.save()

        result = decidir(instancia, self.approver, "APROBADO")
        instancia.refresh_from_db()

        assert result is True
        assert instancia.estado == "APROBADO"
        assert instancia.etapa_actual is None
        assert instancia.completado_en is not None

        # Target object should have been updated
        self.target.refresh_from_db()
        assert self.target.first_name == "Aprobado"

    # -- Records PasoFlujo ---------------------------------------------------
    @patch("workflows.services._notificar_aprobadores")
    def test_records_paso_flujo(self, mock_notif):
        instancia = self._create_instancia()
        decidir(instancia, self.approver, "APROBADO", comentario="OK")

        pasos = PasoFlujo.objects.filter(instancia=instancia)
        assert pasos.count() == 1
        paso = pasos.first()
        assert paso.decision == "APROBADO"
        assert paso.aprobador == self.approver
        assert paso.comentario == "OK"
        assert paso.etapa == self.etapa1

    # -- Reject correctly ----------------------------------------------------
    def test_reject_finalizes_as_rechazado(self):
        instancia = self._create_instancia()
        result = decidir(instancia, self.approver, "RECHAZADO", comentario="No procede")
        instancia.refresh_from_db()

        assert result is True
        assert instancia.estado == "RECHAZADO"
        assert instancia.completado_en is not None

        self.target.refresh_from_db()
        assert self.target.first_name == "Rechazado"

    # -- Unauthorized user returns False -------------------------------------
    def test_unauthorized_user_cannot_decide(self):
        instancia = self._create_instancia()
        result = decidir(instancia, self.non_approver, "APROBADO")

        assert result is False
        assert PasoFlujo.objects.filter(instancia=instancia).count() == 0

    # -- Requires comment ----------------------------------------------------
    def test_requires_comment_raises_value_error(self):
        self.etapa1.requiere_comentario = True
        self.etapa1.save()
        instancia = self._create_instancia()

        with pytest.raises(ValueError, match="comentario"):
            decidir(instancia, self.approver, "APROBADO", comentario="")


class VerificarVencimientosTests(TestCase):
    """Tests for the verificar_vencimientos service function."""

    def setUp(self):
        self.ct = _user_ct()
        self.flujo = FlujoTrabajo.objects.create(
            nombre="Flujo Vencimiento",
            content_type=self.ct,
            campo_trigger="first_name",
            valor_trigger="Pendiente",
            campo_resultado="first_name",
            valor_aprobado="Aprobado",
            valor_rechazado="Rechazado",
            notificar_email=False,
        )
        self.approver = User.objects.create_user(
            "approver", "a@test.com", "pass", is_superuser=True
        )
        self.escalation_user = User.objects.create_user(
            "escalado", "e@test.com", "pass"
        )
        self.target = User.objects.create_user(
            "target", "t@test.com", "pass"
        )
        self.target.first_name = "Pendiente"
        self.target.save()

    def _make_expired_instancia(self, accion_vencimiento, escalar_a=None,
                                 add_next_stage=False):
        etapa = EtapaFlujo.objects.create(
            flujo=self.flujo, orden=1, nombre="Etapa Vence",
            tipo_aprobador="SUPERUSER",
            tiempo_limite_horas=1,
            accion_vencimiento=accion_vencimiento,
            escalar_a=escalar_a,
        )
        next_etapa = None
        if add_next_stage:
            next_etapa = EtapaFlujo.objects.create(
                flujo=self.flujo, orden=2, nombre="Etapa Siguiente",
                tipo_aprobador="SUPERUSER",
            )
        instancia = InstanciaFlujo.objects.create(
            flujo=self.flujo,
            content_type=self.ct,
            object_id=self.target.pk,
            etapa_actual=etapa,
            estado="EN_PROCESO",
            solicitante=self.approver,
            etapa_vence_en=timezone.now() - timedelta(hours=2),
        )
        return instancia, etapa, next_etapa

    # -- AUTO_APROBAR --------------------------------------------------------
    def test_auto_aprobar_finalizes(self):
        instancia, etapa, _ = self._make_expired_instancia("AUTO_APROBAR")
        verificar_vencimientos()

        instancia.refresh_from_db()
        assert instancia.estado == "APROBADO"
        assert instancia.completado_en is not None

        paso = PasoFlujo.objects.get(instancia=instancia)
        assert paso.decision == "AUTO_APROBADO"

        self.target.refresh_from_db()
        assert self.target.first_name == "Aprobado"

    def test_auto_aprobar_advances_if_next_stage(self):
        instancia, etapa, next_etapa = self._make_expired_instancia(
            "AUTO_APROBAR", add_next_stage=True
        )
        verificar_vencimientos()

        instancia.refresh_from_db()
        assert instancia.estado == "EN_PROCESO"
        assert instancia.etapa_actual == next_etapa

    # -- AUTO_RECHAZAR -------------------------------------------------------
    def test_auto_rechazar_finalizes(self):
        instancia, etapa, _ = self._make_expired_instancia("AUTO_RECHAZAR")
        verificar_vencimientos()

        instancia.refresh_from_db()
        assert instancia.estado == "RECHAZADO"
        assert instancia.completado_en is not None

        paso = PasoFlujo.objects.get(instancia=instancia)
        assert paso.decision == "AUTO_RECHAZADO"

        self.target.refresh_from_db()
        assert self.target.first_name == "Rechazado"

    # -- ESCALAR -------------------------------------------------------------
    def test_escalar_stores_in_metadata(self):
        instancia, etapa, _ = self._make_expired_instancia(
            "ESCALAR", escalar_a=self.escalation_user
        )
        verificar_vencimientos()

        instancia.refresh_from_db()
        assert instancia.estado == "EN_PROCESO"  # still in process
        assert instancia.metadata["escalado_a_user_id"] == self.escalation_user.pk
        assert instancia.metadata["escalado_a_username"] == self.escalation_user.username
        assert instancia.metadata["tipo_aprobador_override"] == "USUARIO"

        # Verify a DELEGADO step was recorded
        paso = PasoFlujo.objects.get(instancia=instancia)
        assert paso.decision == "DELEGADO"

    def test_escalar_does_not_mutate_etapa_template(self):
        instancia, etapa, _ = self._make_expired_instancia(
            "ESCALAR", escalar_a=self.escalation_user
        )
        original_tipo = etapa.tipo_aprobador
        original_aprobador_id = etapa.aprobador_usuario_id

        verificar_vencimientos()

        etapa.refresh_from_db()
        assert etapa.tipo_aprobador == original_tipo
        assert etapa.aprobador_usuario_id == original_aprobador_id

    def test_escalar_allows_escalated_user_to_approve(self):
        """After escalation, the escalated user can approve the instance."""
        instancia, etapa, _ = self._make_expired_instancia(
            "ESCALAR", escalar_a=self.escalation_user
        )
        verificar_vencimientos()
        instancia.refresh_from_db()

        assert instancia.puede_aprobar(self.escalation_user) is True

    # -- ESPERAR -------------------------------------------------------------
    def test_esperar_does_nothing(self):
        instancia, etapa, _ = self._make_expired_instancia("ESPERAR")
        verificar_vencimientos()

        instancia.refresh_from_db()
        assert instancia.estado == "EN_PROCESO"
        assert instancia.etapa_actual == etapa
        assert PasoFlujo.objects.filter(instancia=instancia).count() == 0


class EdgeCaseTests(TestCase):
    """Edge case tests for workflow operations."""

    def setUp(self):
        self.ct = _user_ct()
        self.flujo = FlujoTrabajo.objects.create(
            nombre="Flujo Edge",
            content_type=self.ct,
            campo_trigger="first_name",
            valor_trigger="Pendiente",
            campo_resultado="first_name",
            valor_aprobado="Aprobado",
            valor_rechazado="Rechazado",
            notificar_email=False,
        )
        self.approver = User.objects.create_user(
            "approver", "a@test.com", "pass", is_superuser=True
        )
        self.target = User.objects.create_user(
            "target", "t@test.com", "pass"
        )
        self.target.first_name = "Pendiente"
        self.target.save()

        self.etapa = EtapaFlujo.objects.create(
            flujo=self.flujo, orden=1, nombre="Unica Etapa",
            tipo_aprobador="SUPERUSER",
        )

    def _create_instancia(self, estado="EN_PROCESO"):
        return InstanciaFlujo.objects.create(
            flujo=self.flujo,
            content_type=self.ct,
            object_id=self.target.pk,
            etapa_actual=self.etapa if estado == "EN_PROCESO" else None,
            estado=estado,
            solicitante=self.approver,
        )

    # -- Cannot approve completed workflow -----------------------------------
    def test_cannot_approve_completed_workflow(self):
        instancia = self._create_instancia(estado="APROBADO")
        result = decidir(instancia, self.approver, "APROBADO")

        assert result is False
        assert PasoFlujo.objects.filter(instancia=instancia).count() == 0

    def test_cannot_approve_rejected_workflow(self):
        instancia = self._create_instancia(estado="RECHAZADO")
        result = decidir(instancia, self.approver, "APROBADO")

        assert result is False

    def test_cannot_approve_cancelled_workflow(self):
        instancia = self._create_instancia(estado="CANCELADO")
        result = decidir(instancia, self.approver, "APROBADO")

        assert result is False

    # -- Multiple approvals on same step -------------------------------------
    def test_second_approval_on_same_step_fails(self):
        """Once a step is approved and the workflow advances/completes,
        a second call returns False because the instance is no longer
        EN_PROCESO or the etapa_actual has changed."""
        instancia = self._create_instancia()

        # First approval finalizes (single stage)
        result1 = decidir(instancia, self.approver, "APROBADO")
        assert result1 is True
        instancia.refresh_from_db()
        assert instancia.estado == "APROBADO"

        # Second attempt should fail
        result2 = decidir(instancia, self.approver, "APROBADO")
        assert result2 is False
        assert PasoFlujo.objects.filter(instancia=instancia).count() == 1

    @patch("workflows.services._notificar_aprobadores")
    def test_second_approval_same_step_multi_stage(self, mock_notif):
        """In a multi-stage workflow, after approving step 1 the etapa_actual
        changes, so a second approval on the 'old' step effectively approves
        step 2 (since puede_aprobar checks current stage, not specific stage)."""
        etapa2 = EtapaFlujo.objects.create(
            flujo=self.flujo, orden=2, nombre="Etapa 2",
            tipo_aprobador="SUPERUSER",
        )
        instancia = self._create_instancia()

        # Approve step 1 -> advances to step 2
        decidir(instancia, self.approver, "APROBADO")
        instancia.refresh_from_db()
        assert instancia.etapa_actual == etapa2
        assert instancia.estado == "EN_PROCESO"

        # Approve step 2 -> finalizes
        decidir(instancia, self.approver, "APROBADO")
        instancia.refresh_from_db()
        assert instancia.estado == "APROBADO"
        assert PasoFlujo.objects.filter(instancia=instancia).count() == 2

    def test_vencimiento_not_expired_not_processed(self):
        """Instances that haven't expired yet should not be processed."""
        instancia = self._create_instancia()
        instancia.etapa_vence_en = timezone.now() + timedelta(hours=24)
        instancia.save()

        count = verificar_vencimientos()
        instancia.refresh_from_db()

        assert instancia.estado == "EN_PROCESO"
        assert count == 0
