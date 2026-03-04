from django.contrib import admin
from .models import (
    PlantillaOnboarding, PasoPlantilla,
    ProcesoOnboarding, PasoOnboarding,
    PlantillaOffboarding, PasoPlantillaOff,
    ProcesoOffboarding, PasoOffboarding,
)

admin.site.register(PlantillaOnboarding)
admin.site.register(PasoPlantilla)
admin.site.register(ProcesoOnboarding)
admin.site.register(PasoOnboarding)
admin.site.register(PlantillaOffboarding)
admin.site.register(PasoPlantillaOff)
admin.site.register(ProcesoOffboarding)
admin.site.register(PasoOffboarding)
