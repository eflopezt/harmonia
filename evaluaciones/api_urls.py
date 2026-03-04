"""
API URLs — Evaluaciones.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .api_views import (
    CompetenciaViewSet, CicloEvaluacionViewSet, EvaluacionViewSet,
    ResultadoConsolidadoViewSet, PlanDesarrolloViewSet,
    ObjetivoClaveViewSet, ResultadoClaveViewSet, CheckInOKRViewSet,
)

router = DefaultRouter()
router.register(r'competencias', CompetenciaViewSet, basename='competencia')
router.register(r'ciclos', CicloEvaluacionViewSet, basename='ciclo-evaluacion')
router.register(r'evaluaciones', EvaluacionViewSet, basename='evaluacion')
router.register(r'resultados', ResultadoConsolidadoViewSet, basename='resultado')
router.register(r'planes', PlanDesarrolloViewSet, basename='plan-desarrollo')
router.register(r'okrs', ObjetivoClaveViewSet, basename='okr')
router.register(r'okrs-kr', ResultadoClaveViewSet, basename='okr-kr')
router.register(r'okrs-checkins', CheckInOKRViewSet, basename='okr-checkin')

urlpatterns = [
    path('', include(router.urls)),
]
