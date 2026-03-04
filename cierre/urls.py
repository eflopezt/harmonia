from django.urls import path
from cierre import views

urlpatterns = [
    path('',                              views.cierre_lista,          name='cierre_lista'),
    path('dashboard/',                    views.cierre_dashboard,      name='cierre_dashboard'),
    path('crear/',                        views.cierre_crear,          name='cierre_crear'),
    path('<int:pk>/',                     views.cierre_wizard,         name='cierre_wizard'),
    path('<int:pk>/reabrir/',             views.cierre_reabrir,        name='cierre_reabrir'),
    path('<int:pk>/ejecutar/<str:codigo>/', views.cierre_ejecutar_paso, name='cierre_ejecutar_paso'),
    path('<int:pk>/ejecutar-todos/',      views.cierre_ejecutar_todos, name='cierre_ejecutar_todos'),
    path('<int:pk>/resumen/',             views.cierre_resumen,        name='cierre_resumen'),
    path('<int:pk>/checklist/',           views.cierre_checklist_ajax, name='cierre_checklist'),
    path('<int:pk>/validar/',             views.cierre_validar,        name='cierre_validar'),
    path('<int:pk>/rezagos/',             views.cierre_rezagos,        name='cierre_rezagos'),
]
