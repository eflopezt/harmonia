from django.contrib import admin
from .models import (
    CategoriaCapacitacion, Capacitacion, AsistenciaCapacitacion,
    RequerimientoCapacitacion, CertificacionTrabajador
)

admin.site.register(CategoriaCapacitacion)
admin.site.register(Capacitacion)
admin.site.register(AsistenciaCapacitacion)
admin.site.register(RequerimientoCapacitacion)
admin.site.register(CertificacionTrabajador)
