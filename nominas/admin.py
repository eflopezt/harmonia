from django.contrib import admin
from .models import ConceptoRemunerativo, PeriodoNomina, RegistroNomina, LineaNomina

admin.site.register(ConceptoRemunerativo)
admin.site.register(PeriodoNomina)
admin.site.register(RegistroNomina)
admin.site.register(LineaNomina)
