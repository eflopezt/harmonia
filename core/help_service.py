"""
Harmoni ERP — Contextual Help Service
Provides per-view help content, tips, and guided tour definitions.
"""

HELP_CONTENT = {
    # ── Dashboard / Home ──────────────────────────────────────────
    'home': {
        'title': 'Dashboard Principal',
        'icon': 'fa-th-large',
        'description': (
            'Tu centro de mando. Aqui ves un resumen de toda la gestion '
            'de RRHH: headcount, asistencia, tareas pendientes y alertas.'
        ),
        'tips': [
            'Los widgets se actualizan automaticamente cada vez que entras.',
            'Usa Ctrl+K para busqueda rapida de empleados o modulos.',
            'El asistente IA (boton verde abajo a la derecha) puede responder preguntas sobre tu planilla.',
            'Las alertas rojas requieren atencion inmediata; las amarillas son preventivas.',
        ],
        'shortcuts': [
            {'keys': 'Ctrl+K', 'action': 'Busqueda global'},
            {'keys': 'F1', 'action': 'Abrir panel de ayuda'},
        ],
        'related_links': [
            {'label': 'Analytics', 'url': '/analytics/', 'icon': 'fa-chart-bar'},
            {'label': 'Personal', 'url': '/personal/', 'icon': 'fa-users'},
        ],
        'video_url': None,
    },

    # ── Personal ──────────────────────────────────────────────────
    'personal_list': {
        'title': 'Gestion de Personal',
        'icon': 'fa-users',
        'description': (
            'Aqui puedes ver y gestionar todos los colaboradores de la empresa. '
            'Filtra por area, estado, tipo de contrato y mas.'
        ),
        'tips': [
            'Usa el buscador para encontrar por DNI, nombre o apellido.',
            'Haz clic en el nombre del colaborador para ver su ficha completa.',
            'Puedes exportar la lista a Excel con el boton de descarga.',
            'Los indicadores de color muestran el estado: verde=activo, rojo=cesado.',
            'Para registrar un nuevo colaborador, usa el boton "+ Nuevo".',
        ],
        'shortcuts': [],
        'related_links': [
            {'label': 'Importar desde Excel', 'url': '/personal/importar/', 'icon': 'fa-file-excel'},
            {'label': 'Organigrama', 'url': '/personal/organigrama/', 'icon': 'fa-sitemap'},
        ],
        'video_url': None,
    },
    'personal_detail': {
        'title': 'Ficha del Colaborador',
        'icon': 'fa-user',
        'description': (
            'Ficha completa del colaborador con toda su informacion laboral, '
            'documentos, historial salarial y mas.'
        ),
        'tips': [
            'Las pestanas organizan la informacion: datos personales, laboral, documentos, etc.',
            'Puedes editar campos haciendo clic en el boton "Editar".',
            'Los cambios importantes quedan registrados en el log de auditoria.',
            'Desde aqui puedes generar la boleta de pago o constancia laboral.',
        ],
        'shortcuts': [],
        'related_links': [],
        'video_url': None,
    },

    # ── Asistencia / Tareo ────────────────────────────────────────
    'asistencia_tareo': {
        'title': 'Control de Asistencia',
        'icon': 'fa-fingerprint',
        'description': (
            'Registra y gestiona la asistencia diaria del personal. '
            'Visualiza marcaciones, tardanzas, faltas y horas extras.'
        ),
        'tips': [
            'El tareo muestra el estado diario de cada colaborador por colores.',
            'Verde = asistencia normal, Amarillo = tardanza, Rojo = falta.',
            'Puedes filtrar por area, fecha o tipo de incidencia.',
            'Las papeletas de permiso se gestionan desde la seccion Papeletas.',
            'El banco de horas registra automaticamente las horas extras.',
            'Si tienes reloj biometrico configurado, las marcaciones se sincronizan automaticamente.',
        ],
        'shortcuts': [],
        'related_links': [
            {'label': 'Papeletas', 'url': '/asistencia/papeletas/', 'icon': 'fa-file-alt'},
            {'label': 'Banco de Horas', 'url': '/asistencia/banco-horas/', 'icon': 'fa-clock'},
        ],
        'video_url': None,
    },

    # ── Nominas / Planilla ────────────────────────────────────────
    'nominas_panel': {
        'title': 'Nominas y Planilla',
        'icon': 'fa-money-check-alt',
        'description': (
            'Genera y gestiona la planilla de remuneraciones. Calcula conceptos '
            'remunerativos, descuentos AFP/ONP, IR 5ta categoria y aportes del empleador.'
        ),
        'tips': [
            'Primero crea o selecciona un periodo de nomina (mensual, quincenal, etc.).',
            'Usa "Calcular Nomina" para generar todos los registros del periodo.',
            'Revisa las lineas de nomina antes de cerrar el periodo.',
            'Las boletas de pago se generan en PDF individualmente o en lote.',
            'Los conceptos remunerativos se configuran en el menu de Conceptos.',
            'Recuerda: RMV vigente S/ 1,130 (DS 006-2024-TR). UIT 2026: S/ 5,500.',
        ],
        'shortcuts': [],
        'related_links': [
            {'label': 'Conceptos Remunerativos', 'url': '/nominas/conceptos/', 'icon': 'fa-list'},
            {'label': 'Exportar PLAME', 'url': '/integraciones/plame/', 'icon': 'fa-file-invoice'},
        ],
        'video_url': None,
    },

    # ── Vacaciones ────────────────────────────────────────────────
    'vacaciones_panel': {
        'title': 'Gestion de Vacaciones',
        'icon': 'fa-umbrella-beach',
        'description': (
            'Administra las solicitudes de vacaciones, saldos vacacionales '
            'y calendario de ausencias del equipo.'
        ),
        'tips': [
            'El saldo vacacional se calcula automaticamente segun la fecha de ingreso.',
            'Los colaboradores pueden solicitar vacaciones desde su portal.',
            'El flujo de aprobacion va: Colaborador -> Jefe de Area -> RRHH.',
            'Puedes ver el calendario de ausencias para evitar cruces de fechas.',
            'Las vacaciones truncas se calculan al momento del cese.',
            'Por ley, el trabajador tiene derecho a 30 dias por ano completo.',
        ],
        'shortcuts': [],
        'related_links': [
            {'label': 'Calendario', 'url': '/calendario/', 'icon': 'fa-calendar-alt'},
            {'label': 'Saldos Vacacionales', 'url': '/vacaciones/saldos/', 'icon': 'fa-balance-scale'},
        ],
        'video_url': None,
    },

    # ── Documentos ────────────────────────────────────────────────
    'documentos_panel': {
        'title': 'Gestion Documental',
        'icon': 'fa-folder-open',
        'description': (
            'Almacena, organiza y gestiona todos los documentos del area de RRHH. '
            'Contratos, adendas, constancias y mas.'
        ),
        'tips': [
            'Arrastra archivos directamente para subirlos.',
            'Los documentos se organizan por tipo y por colaborador.',
            'Puedes generar constancias y certificados automaticamente.',
            'Los documentos con fecha de vencimiento generan alertas automaticas.',
            'Formatos aceptados: PDF, Word, Excel, imagenes.',
        ],
        'shortcuts': [],
        'related_links': [],
        'video_url': None,
    },

    # ── Analytics ─────────────────────────────────────────────────
    'analytics_dashboard': {
        'title': 'Analytics y Reportes',
        'icon': 'fa-chart-bar',
        'description': (
            'Panel de indicadores clave (KPIs) de gestion humana. '
            'Headcount, rotacion, ausentismo, costos y tendencias.'
        ),
        'tips': [
            'Los graficos son interactivos: pasa el cursor para ver detalles.',
            'Usa los filtros de fecha para comparar periodos.',
            'Los KPI Snapshots se guardan automaticamente el primer dia de cada mes.',
            'Las alertas de RRHH se generan automaticamente cuando un indicador sale del rango.',
            'El modulo de Riesgo de Fuga usa IA para predecir posibles renuncias.',
            'Puedes exportar cualquier reporte a Excel o PDF.',
        ],
        'shortcuts': [],
        'related_links': [
            {'label': 'Headcount', 'url': '/analytics/headcount/', 'icon': 'fa-users'},
            {'label': 'Riesgo de Fuga', 'url': '/analytics/attrition/', 'icon': 'fa-user-slash'},
            {'label': 'Dashboard IA', 'url': '/analytics/ia/', 'icon': 'fa-robot'},
        ],
        'video_url': None,
    },

    # ── Workflows ─────────────────────────────────────────────────
    'workflows_panel': {
        'title': 'Workflows y Aprobaciones',
        'icon': 'fa-code-branch',
        'description': (
            'Flujos de aprobacion configurables para solicitudes de vacaciones, '
            'permisos, cambios salariales y mas.'
        ),
        'tips': [
            'Cada tipo de solicitud puede tener su propio flujo de aprobacion.',
            'Los aprobadores reciben notificaciones automaticas.',
            'Puedes ver el historial completo de aprobaciones y rechazos.',
            'Los workflows vencidos se escalan automaticamente al siguiente nivel.',
            'Configura los flujos desde Administracion > Config. Workflows.',
        ],
        'shortcuts': [],
        'related_links': [
            {'label': 'Config. Workflows', 'url': '/workflows/config/', 'icon': 'fa-project-diagram'},
            {'label': 'Aprobaciones', 'url': '/aprobaciones/', 'icon': 'fa-check-circle'},
        ],
        'video_url': None,
    },

    # ── AI Chat ───────────────────────────────────────────────────
    'ai_chat': {
        'title': 'Asistente IA de RRHH',
        'icon': 'fa-robot',
        'description': (
            'Chat inteligente que responde preguntas sobre tu planilla, personal, '
            'asistencia y normativa laboral peruana. Soporta imagenes (OCR) y PDFs.'
        ),
        'tips': [
            'Escribe preguntas en lenguaje natural: "Cuantos empleados tenemos?"',
            'Puedes adjuntar imagenes y el asistente extraera texto con OCR.',
            'Sube un PDF y pidele que lo analice o edite.',
            'El asistente conoce la normativa laboral peruana vigente.',
            'Prueba: "Genera la boleta de Juan Perez" o "Cuanto se paga de CTS?"',
            'Las respuestas se basan en datos reales de tu empresa.',
        ],
        'shortcuts': [],
        'related_links': [],
        'video_url': None,
    },

    # ── Reclutamiento ─────────────────────────────────────────────
    'reclutamiento_panel': {
        'title': 'Reclutamiento y Seleccion',
        'icon': 'fa-briefcase',
        'description': (
            'Gestiona todo el proceso de reclutamiento: publicacion de vacantes, '
            'recepcion de postulaciones, entrevistas y contratacion.'
        ),
        'tips': [
            'Crea una vacante y comparte el enlace publico con los candidatos.',
            'El pipeline visual muestra en que etapa esta cada candidato.',
            'Puedes programar entrevistas y enviar notificaciones automaticas.',
            'Al contratar, el candidato se convierte en colaborador automaticamente.',
        ],
        'shortcuts': [],
        'related_links': [],
        'video_url': None,
    },

    # ── Capacitaciones ────────────────────────────────────────────
    'capacitaciones_panel': {
        'title': 'Capacitaciones',
        'icon': 'fa-graduation-cap',
        'description': (
            'Planifica y registra las capacitaciones del personal. '
            'Controla asistencia, evaluaciones y certificaciones.'
        ),
        'tips': [
            'Crea programas de capacitacion y asigna participantes.',
            'Registra la asistencia y evaluacion de cada sesion.',
            'Genera certificados automaticos al completar un programa.',
        ],
        'shortcuts': [],
        'related_links': [],
        'video_url': None,
    },

    # ── Evaluaciones ──────────────────────────────────────────────
    'evaluaciones_panel': {
        'title': 'Evaluaciones de Desempeno',
        'icon': 'fa-star',
        'description': (
            'Configura y ejecuta evaluaciones de desempeno 360, '
            'por objetivos o por competencias.'
        ),
        'tips': [
            'Define los criterios de evaluacion antes de iniciar una campana.',
            'Las evaluaciones 360 incluyen autoevaluacion, jefe, pares y subordinados.',
            'Los resultados se consolidan automaticamente en graficos.',
        ],
        'shortcuts': [],
        'related_links': [],
        'video_url': None,
    },

    # ── Onboarding ────────────────────────────────────────────────
    'onboarding_panel': {
        'title': 'Onboarding',
        'icon': 'fa-door-open',
        'description': (
            'Gestiona el proceso de incorporacion de nuevos colaboradores. '
            'Checklists, documentos pendientes y seguimiento.'
        ),
        'tips': [
            'Cada nuevo colaborador recibe un checklist automatico.',
            'Puedes personalizar las tareas del onboarding por cargo o area.',
            'El dashboard muestra el avance de cada proceso activo.',
        ],
        'shortcuts': [],
        'related_links': [],
        'video_url': None,
    },

    # ── Disciplinaria ─────────────────────────────────────────────
    'disciplinaria_panel': {
        'title': 'Procesos Disciplinarios',
        'icon': 'fa-gavel',
        'description': (
            'Registra y gestiona amonestaciones, memorandos y '
            'procesos disciplinarios del personal.'
        ),
        'tips': [
            'Cada accion disciplinaria queda registrada en el historial del colaborador.',
            'Puedes adjuntar documentos de descargo.',
            'Los flujos de aprobacion aseguran el debido proceso.',
        ],
        'shortcuts': [],
        'related_links': [],
        'video_url': None,
    },

    # ── Prestamos ─────────────────────────────────────────────────
    'prestamos_panel': {
        'title': 'Prestamos al Personal',
        'icon': 'fa-hand-holding-usd',
        'description': (
            'Gestiona prestamos y adelantos de sueldo. '
            'Controla cuotas, saldos y descuentos automaticos en planilla.'
        ),
        'tips': [
            'Los descuentos de cuotas se aplican automaticamente en la nomina.',
            'Puedes configurar el numero maximo de cuotas y tasa de interes.',
            'El sistema calcula el saldo pendiente en tiempo real.',
        ],
        'shortcuts': [],
        'related_links': [],
        'video_url': None,
    },

    # ── Salarios ──────────────────────────────────────────────────
    'salarios_panel': {
        'title': 'Gestion Salarial',
        'icon': 'fa-money-bill-wave',
        'description': (
            'Bandas salariales, simulaciones de incremento, analisis de equidad '
            'y historial salarial del personal.'
        ),
        'tips': [
            'Las bandas salariales te ayudan a mantener equidad interna.',
            'Usa el simulador para proyectar el impacto de incrementos.',
            'El analisis de equidad detecta brechas por genero o area.',
        ],
        'shortcuts': [],
        'related_links': [],
        'video_url': None,
    },
}

# ── Guided Tour Definitions ──────────────────────────────────────
GUIDED_TOURS = {
    'dashboard': {
        'id': 'dashboard_tour',
        'name': 'Conoce tu Dashboard',
        'steps': [
            {
                'target': '#harmoniSidebar',
                'title': 'Menu lateral',
                'content': 'Desde aqui accedes a todos los modulos: Personal, Asistencia, Nominas, Vacaciones y mas.',
                'position': 'right',
            },
            {
                'target': '#globalSearchInput',
                'title': 'Busqueda rapida',
                'content': 'Busca cualquier empleado por nombre o DNI. Tambien puedes usar Ctrl+K para la busqueda avanzada.',
                'position': 'bottom',
            },
            {
                'target': '.topbar-actions',
                'title': 'Notificaciones',
                'content': 'Aqui ves las notificaciones pendientes: aprobaciones, alertas y comunicados.',
                'position': 'bottom',
            },
            {
                'target': '.harmoni-content',
                'title': 'Area de trabajo',
                'content': 'Este es tu espacio principal. Los widgets muestran KPIs, tareas pendientes y alertas importantes.',
                'position': 'top',
            },
        ],
    },
    'personal_list': {
        'id': 'personal_list_tour',
        'name': 'Lista de Personal',
        'steps': [
            {
                'target': '.dataTables_filter input, .dt-search input, input[type="search"]',
                'title': 'Buscador de empleados',
                'content': 'Filtra la tabla por nombre, DNI, area o cualquier dato visible.',
                'position': 'bottom',
            },
            {
                'target': '.btn-primary, a[href*="nuevo"], a[href*="crear"]',
                'title': 'Nuevo colaborador',
                'content': 'Haz clic aqui para registrar un nuevo colaborador en el sistema.',
                'position': 'left',
            },
        ],
    },
    'nominas_panel': {
        'id': 'nominas_tour',
        'name': 'Panel de Nominas',
        'steps': [
            {
                'target': '.card, .periodo-card, [data-periodo]',
                'title': 'Periodos de nomina',
                'content': 'Selecciona un periodo para ver o calcular la planilla. Los periodos abiertos estan en verde.',
                'position': 'bottom',
            },
            {
                'target': 'a[href*="conceptos"], .btn-conceptos',
                'title': 'Conceptos remunerativos',
                'content': 'Configura los conceptos que componen la planilla: basico, asignaciones, descuentos, etc.',
                'position': 'bottom',
            },
        ],
    },
}


def get_help_for_view(view_key):
    """Return help content for a specific view, with safe defaults."""
    default = {
        'title': 'Ayuda',
        'icon': 'fa-question-circle',
        'description': 'Usa el menu lateral para navegar entre modulos.',
        'tips': ['Presiona Ctrl+K para busqueda rapida.'],
        'shortcuts': [],
        'related_links': [],
        'video_url': None,
    }
    return HELP_CONTENT.get(view_key, default)


def get_tour_for_view(view_key):
    """Return guided tour definition for a view, or None."""
    return GUIDED_TOURS.get(view_key)


def get_help_context(view_key):
    """
    Build the full template context for help components.
    Use in views: context.update(get_help_context('personal_list'))
    """
    import json
    help_data = get_help_for_view(view_key)
    tour_data = get_tour_for_view(view_key)
    return {
        'help_key': view_key,
        'help_data': help_data,
        'help_tour': tour_data,
        'help_tour_json': json.dumps(tour_data) if tour_data else 'null',
    }
