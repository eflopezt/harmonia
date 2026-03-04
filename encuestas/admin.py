from django.contrib import admin
from .models import Encuesta, PreguntaEncuesta, RespuestaEncuesta, ResultadoEncuesta

admin.site.register(Encuesta)
admin.site.register(PreguntaEncuesta)
admin.site.register(RespuestaEncuesta)
admin.site.register(ResultadoEncuesta)
