from django.contrib import admin
from .models import SaldoVacacional, TipoPermiso, SolicitudVacacion, SolicitudPermiso, VentaVacaciones

admin.site.register(SaldoVacacional)
admin.site.register(TipoPermiso)
admin.site.register(SolicitudVacacion)
admin.site.register(SolicitudPermiso)
admin.site.register(VentaVacaciones)
