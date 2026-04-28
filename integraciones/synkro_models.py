"""
Modelos unmanaged sobre la BD del sistema Synkro (Sistema de Control de
Personal y Asistencias / SistemaRRHHCSRT). Solo lectura.

La BD vive en SQL Server remoto y se accede vía la connection 'synkro'
configurada en settings.production. Si no hay credenciales (SYNKRO_HOST
no definido), las queries fallarán — la integración debe estar gateada.

Solo se exponen las tablas que necesita el sync: maestro de personal,
picadas biométricas, papeletas y feriados.
"""
from django.db import models


class PerPersona(models.Model):
    """Persona física — maestro central. Match con Personal.nro_doc por Dni."""
    id_persona = models.IntegerField(primary_key=True, db_column='IdPersona')
    dni = models.CharField(max_length=20, db_column='Dni')
    a_paterno = models.CharField(max_length=100, db_column='APaterno', blank=True, null=True)
    a_materno = models.CharField(max_length=100, db_column='AMaterno', blank=True, null=True)
    nombres = models.CharField(max_length=150, db_column='Nombres', blank=True, null=True)
    nombre_completo = models.CharField(max_length=300, db_column='NombreCompleto', blank=True, null=True)
    celular = models.CharField(max_length=30, db_column='Celular', blank=True, null=True)
    correo = models.CharField(max_length=200, db_column='Correo', blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'PER_Personas'


class PPersonal(models.Model):
    """Vínculo laboral con Synkro: ingreso, contrato, cese, tipo trabajador.

    IdTipoTrabajador: 2=Obrero (construcción civil, NO importar a Harmoni),
                      3=Empleado (sí importar).
    """
    id_personal = models.IntegerField(primary_key=True, db_column='IdPersonal')
    id_persona = models.IntegerField(db_column='IdPersona')
    estado = models.BooleanField(db_column='Estado')
    id_tipo_trabajador = models.IntegerField(db_column='IdTipoTrabajador', blank=True, null=True)
    fecha_ingreso = models.DateField(db_column='FechaIngreso', blank=True, null=True)
    fecha_termino_contrato = models.DateField(db_column='FechaTerminoContrato', blank=True, null=True)
    motivo_cese = models.CharField(max_length=200, db_column='MotivoCese', blank=True, null=True)
    codigo = models.CharField(max_length=20, db_column='Codigo', blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'P_Personal'


class PicadoPersonal(models.Model):
    """Marcación biométrica individual (ingreso o salida)."""
    id_picado = models.IntegerField(primary_key=True, db_column='IdPicado')
    id_personal = models.IntegerField(db_column='IdPersonal')
    fecha = models.DateTimeField(db_column='Fecha')
    hora_picado = models.IntegerField(db_column='HoraPicado', blank=True, null=True)
    fecha_sin_ms = models.DateField(db_column='FechaSinMS')
    id_tipo = models.IntegerField(db_column='IdTipo', blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'PicadosPersonal'


class TipoPermiso(models.Model):
    id_tipo_permiso = models.IntegerField(primary_key=True, db_column='IdTipoPermiso')
    descripcion = models.CharField(max_length=200, db_column='Descripcion')
    iniciales = models.CharField(max_length=10, db_column='Iniciales')

    class Meta:
        managed = False
        db_table = 'TiposPermiso'


class PermisoLicencia(models.Model):
    """Papeletas / licencias / permisos."""
    id_permiso = models.IntegerField(primary_key=True, db_column='IdPermiso')
    id_personal = models.IntegerField(db_column='IdPersonal')
    id_tipo_permiso = models.IntegerField(db_column='IdTipoPermiso')
    fecha_inicio = models.DateField(db_column='FechaInicio')
    fecha_fin = models.DateField(db_column='FechaFin')
    detalle = models.CharField(max_length=500, db_column='Detalle', blank=True, null=True)
    fecha_registro = models.DateTimeField(db_column='FechaRegistro', blank=True, null=True)
    fecha_modifica = models.DateTimeField(db_column='FechaModifica', blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'PermisosLicencias'


class FeriadoSynkro(models.Model):
    id_feriado = models.IntegerField(primary_key=True, db_column='IdFeriado')
    fecha = models.DateField(db_column='Fecha')
    descripcion = models.CharField(max_length=200, db_column='Descripcion', blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'Feriados'
