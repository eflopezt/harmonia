from django.contrib import admin
from .models import BandaSalarial, HistorialSalarial, SimulacionIncremento, DetalleSimulacion

admin.site.register(BandaSalarial)
admin.site.register(HistorialSalarial)
admin.site.register(SimulacionIncremento)
admin.site.register(DetalleSimulacion)
