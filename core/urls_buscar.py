"""
Shortcut URL file: mounts global-search views at /buscar/
so the top-bar JS can call /buscar/?q=… and /buscar/pagina/?q=…
without the /sistema/ prefix.
"""
from django.urls import path
from core import views

urlpatterns = [
    path('', views.global_search, name='busqueda_global'),
    path('pagina/', views.busqueda_pagina, name='busqueda_global_pagina'),
]
