from django.contrib import admin
from .models import (
    Competencia, PlantillaEvaluacion, PlantillaCompetencia,
    CicloEvaluacion, Evaluacion, RespuestaEvaluacion,
    ResultadoConsolidado, PlanDesarrollo, AccionDesarrollo,
)

admin.site.register(Competencia)
admin.site.register(PlantillaEvaluacion)
admin.site.register(PlantillaCompetencia)
admin.site.register(CicloEvaluacion)
admin.site.register(Evaluacion)
admin.site.register(RespuestaEvaluacion)
admin.site.register(ResultadoConsolidado)
admin.site.register(PlanDesarrollo)
admin.site.register(AccionDesarrollo)
