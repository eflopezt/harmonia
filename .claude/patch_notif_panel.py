# patch_notif_panel.py  -  replaces notificaciones_panel view body

NEW_FUNC = """\
@solo_admin
def notificaciones_panel(request):
    \"\"\"Dashboard de notificaciones: stats + analítica + tabla reciente con filtros.\"\"\"
    ahora = timezone.now()
    hoy = ahora.date()
    inicio_semana = hoy - timedelta(days=hoy.weekday())
    inicio_mes = hoy.replace(day=1)

    # ── Stats base ──────────────────────────────────────────────────────────────
    qs_all = Notificacion.objects.all()
    total_notifs = qs_all.count()
    enviadas_hoy = qs_all.filter(enviada_en__date=hoy, estado='ENVIADA').count()
    enviadas_semana = qs_all.filter(enviada_en__date__gte=inicio_semana, estado='ENVIADA').count()
    enviadas_mes = qs_all.filter(enviada_en__date__gte=inicio_mes, estado='ENVIADA').count()
    fallidas = qs_all.filter(estado='FALLIDA').count()
    pendientes_in_app = qs_all.filter(tipo='IN_APP', estado='ENVIADA').count()

    # ── Tasa de lectura ─────────────────────────────────────────────────────────
    tasa_lectura_pct = 0
    try:
        total_enviadas = qs_all.filter(estado__in=['ENVIADA', 'LEIDA']).count()
        leidas = qs_all.filter(estado='LEIDA').count()
        if total_enviadas > 0:
            tasa_lectura_pct = round(leidas / total_enviadas * 100, 1)
    except Exception:
        pass

    # ── Comunicados recientes ────────────────────────────────────────────────────
    comunicados_recientes = []
    total_comunicados = 0
    try:
        comunicados_recientes = list(ComunicadoMasivo.objects.order_by('-creado_en')[:5])
        total_comunicados = ComunicadoMasivo.objects.filter(estado='ENVIADO').count()
    except Exception:
        pass

    # ── Distribución por tipo (Email vs In-App) ──────────────────────────────────
    notifs_por_tipo_json = '[]'
    try:
        TIPO_COLORS = {'EMAIL': '#0f766e', 'IN_APP': '#5eead4'}
        tipo_qs = (
            qs_all.values('tipo')
            .annotate(total=Count('id'))
            .order_by('-total')
        )
        notifs_por_tipo_json = json.dumps([
            {
                'label': item['tipo'],
                'value': item['total'],
                'color': TIPO_COLORS.get(item['tipo'], '#94a3b8'),
            }
            for item in tipo_qs
        ])
    except Exception:
        pass

    # ── Tendencia últimos 6 meses ────────────────────────────────────────────────
    notifs_trend_json = '[]'
    try:
        MESES_ES = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun',
                    'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']
        trend_data = []
        # Build 6 month buckets without dateutil (use calendar arithmetic)
        import calendar
        for i in range(5, -1, -1):
            # Walk back i months from current month
            year = ahora.year
            month = ahora.month - i
            while month <= 0:
                month += 12
                year -= 1
            # First day of that month (aware)
            first_day = ahora.replace(
                year=year, month=month, day=1,
                hour=0, minute=0, second=0, microsecond=0
            )
            # Last day of that month
            last_day_num = calendar.monthrange(year, month)[1]
            if i == 0:
                last_day = ahora
            else:
                last_day = ahora.replace(
                    year=year, month=month, day=last_day_num,
                    hour=23, minute=59, second=59, microsecond=999999
                )
            count = qs_all.filter(creado_en__gte=first_day, creado_en__lte=last_day).count()
            trend_data.append({'label': MESES_ES[month - 1], 'total': count})
        notifs_trend_json = json.dumps(trend_data)
    except Exception:
        pass

    # ── Top 5 destinatarios más notificados ─────────────────────────────────────
    destinatarios_top = []
    try:
        top_qs = (
            qs_all.filter(destinatario__isnull=False)
            .values('destinatario__id', 'destinatario__apellidos_nombres')
            .annotate(total=Count('id'))
            .order_by('-total')[:5]
        )
        destinatarios_top = [
            {
                'nombre': item['destinatario__apellidos_nombres'] or '(sin nombre)',
                'total': item['total'],
            }
            for item in top_qs
        ]
    except Exception:
        pass

    # ── Filtros / tabla ──────────────────────────────────────────────────────────
    filtro_tipo = request.GET.get('tipo', '')
    filtro_estado = request.GET.get('estado', '')
    buscar = request.GET.get('q', '')

    qs = qs_all.select_related('destinatario', 'plantilla')
    if filtro_tipo:
        qs = qs.filter(tipo=filtro_tipo)
    if filtro_estado:
        qs = qs.filter(estado=filtro_estado)
    if buscar:
        qs = qs.filter(
            Q(asunto__icontains=buscar) |
            Q(destinatario__apellidos_nombres__icontains=buscar) |
            Q(destinatario_email__icontains=buscar)
        )

    notificaciones = qs[:100]

    return render(request, 'comunicaciones/notificaciones_panel.html', {
        'titulo': 'Notificaciones',
        # stats
        'total_notifs': total_notifs,
        'enviadas_hoy': enviadas_hoy,
        'enviadas_semana': enviadas_semana,
        'enviadas_mes': enviadas_mes,
        'fallidas': fallidas,
        'pendientes_in_app': pendientes_in_app,
        'total_comunicados': total_comunicados,
        'tasa_lectura_pct': tasa_lectura_pct,
        # analytics JSON
        'notifs_por_tipo_json': notifs_por_tipo_json,
        'notifs_trend_json': notifs_trend_json,
        # tables
        'comunicados_recientes': comunicados_recientes,
        'destinatarios_top': destinatarios_top,
        # filters
        'filtro_tipo': filtro_tipo,
        'filtro_estado': filtro_estado,
        'buscar': buscar,
        'notificaciones': notificaciones,
    })
"""


with open('D:/Harmoni/comunicaciones/views.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find the function start (preceded by @login_required\n@solo_admin\n)
OLD_BLOCK_START = '@solo_admin\ndef notificaciones_panel(request):'
assert OLD_BLOCK_START in content, f'Block start not found'

# Find the next section separator after the function
NEXT_SECTION = '\n\n\n# \u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\n# ADMIN \u2014 PLANTILLAS'

start_idx = content.find(OLD_BLOCK_START)
end_idx = content.find(NEXT_SECTION, start_idx)
assert end_idx > start_idx, f'Could not find section end. start={start_idx}'

old_block = content[start_idx:end_idx]
new_content = content[:start_idx] + NEW_FUNC.rstrip('\n') + content[end_idx:]

with open('D:/Harmoni/comunicaciones/views.py', 'w', encoding='utf-8') as f:
    f.write(new_content)

print('SUCCESS: view patched')
print(f'  Replaced {len(old_block)} chars -> {len(NEW_FUNC)} chars')
