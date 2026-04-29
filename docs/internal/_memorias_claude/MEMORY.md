# Harmoni ERP — Memoria del Proyecto

## ¿Qué es Harmoni?
Sistema ERP de RRHH/Planillas para empresas peruanas. Django 5.1 + Bootstrap5 + AI integrado.
Multi-tenant (row-level tenancy por empresa). Ubicación: `D:\Harmoni`

## Stack Técnico
- **Backend**: Django 5.1, Python 3.12, PostgreSQL 16 + pgvector
- **API**: DRF + SimpleJWT + drf-spectacular (OpenAPI)
- **Cache/Broker**: Redis 7 + Celery 5 + Celery Beat
- **Frontend**: Bootstrap5, vanilla JS, PWA (service worker)
- **AI Multi-proveedor**: Gemini 2.0/2.5 Flash, DeepSeek-V3, OpenAI GPT-4o-mini, Ollama
- **PDF/Excel**: ReportLab, xhtml2pdf, pdfminer, pdfplumber, PyMuPDF, pandas, xlsxwriter
- **Deploy**: Docker (multi-stage), VPS Contabo, Gunicorn, WhiteNoise, Sentry

## Producción — VPS Contabo
- **IP**: 212.56.34.166 | **RAM**: 8GB | **CPU**: 4 cores | **Disco**: 72GB
- **SSH**: root + usuario `deploy` (key auth, puerto 22)
- **Dominios**: harmoni.pe, nexotalent.pe (DNS en AQP Hosting, pendiente propagación)
- **SSL**: Activo (Let's Encrypt, auto-renewal via certbot timer)

### Arquitectura del servidor
```
Nginx (:80/:443)
├── harmoni.pe    → Docker harmoni-web (:8000, Gunicorn gthread)
└── nexotalent.pe → Docker nexotalent-web (:8001, Gunicorn+Uvicorn ASGI)

PostgreSQL 16 nativo + pgvector
├── harmoni_db   (user: harmoni)
└── nexotalent_db (user: nexotalent)

Redis 7 nativo (password: H4rm0n1_R3d1s_2026!)
├── DB 0 → Harmoni cache/broker
└── DB 2 → NexoTalent cache/broker

Docker containers (network_mode: host):
├── harmoni-web, harmoni-celery, harmoni-beat
├── nexotalent-web, nexotalent-celery, nexotalent-beat
└── OpenClaw (systemd service)
```

### Archivos de deploy
- `deploy/` — Scripts, configs nginx, postgres tuning, redis, sysctl
- `/opt/harmoni/app/.env.production` — Env vars producción Harmoni
- `/opt/nexotalent/app/.env.production` — Env vars producción NexoTalent
- `COMPOSE_PROJECT_NAME=harmoni` / `nexotalent` — Para separar compose stacks
- `SECURE_SSL_REDIRECT=False` — Temporalmente hasta tener SSL

### Credenciales producción
- **Harmoni admin**: admin / admin123
- **NexoTalent admin**: admin / admin123
- **PostgreSQL**: harmoni/H4rm0n1_Pr0d_2026! | nexotalent/N3x0T4l3nt_Pr0d_2026!
- **Redis**: H4rm0n1_R3d1s_2026!

## 22 Apps Django
analytics, asistencia, calendario, capacitaciones, cierre, comunicaciones, core,
disciplinaria, documentos, empresas, encuestas, evaluaciones, integraciones,
nominas, onboarding, personal, portal, prestamos, reclutamiento, salarios,
vacaciones, viaticos, workflows

## Features Multi-Tenant
- `Empresa` model con SMTP por empresa (Gmail, Office 365, custom)
- `EmpresaEmailBackend` — email backend que lee SMTP de empresa activa
- `EmpresaMiddleware` — inyecta empresa en request + thread-local para email
- Row-level tenancy: Personal.empresa FK, PeriodoNomina.empresa FK

## Normativa Peruana
- UIT 2026: S/ 5,500 | RMV: S/ 1,130
- IR 5ta: escala progresiva en `nominas/engine.py`
- AFP: Habitat 1.55%, Integra 1.55%, Prima 1.60%, Profuturo 1.49% + 10% aporte
- 7 regímenes de turno: 5×2, 14×7, 21×7, 10×4, 4×3, Turno Noche, Rotativo

## NexoTalent (proyecto hermano)
- **Ubicación**: `D:\NexoTalent` | **Dominio**: nexotalent.pe
- SaaS de reclutamiento peruano (13 apps Django)
- Django Channels (WebSocket), Uvicorn ASGI, pgvector, WhatsApp Bot
- Facturación electrónica SUNAT (Nubefact)
- Se trabaja en Claude Desktop (no tocar desde aquí)

## Test Suite (8,692 líneas, 20 archivos, 17 módulos)
- nominas: engine.py (IR 5ta, gratif, AFP) + liquidacion
- vacaciones, workflows, asistencia, personal, empresas
- comunicaciones, documentos, prestamos, salarios
- analytics, core, cierre, onboarding, reclutamiento
- evaluaciones, viaticos

## Bugs Corregidos (sesión 2026-03-15/17)
- CRITICAL: Gratificación descontaba AFP/ONP (Ley 29351)
- HIGH: IR 5ta proyectaba 12x en vez de 14x
- HIGH: asignacion_familiar siempre False en generar_periodo
- HIGH: Workflow escalación mutaba template compartido
- + 7 bugs MEDIUM adicionales en liquidación, vacaciones, nóminas

## Landing Page
- https://harmoni.pe — landing SaaS B2B (glassmorphism, bento grid, animations)
- Login NO visible — cada empresa accede a su instancia exclusiva
- CTA: WhatsApp +51977538028
- Pricing: Starter S/149, Profesional S/349, Enterprise a medida

## Asistencia — Reglas de Negocio (sesión 2026-03-24)
- **Jornadas**: LOCAL L-V 8.5h, Sáb 5.5h | FORÁNEO L-S 10h (efectiva) | Dom 4h
- **SS (Sin Salida)**: jornada completa, 0 HE
- **Marcación incompleta** (<jornada/2): SS implícito
- **Domingo/Feriado**: h.normal hasta jornada + exceso HE 100%
- **Ausencias pagadas** (DL, VAC, LCG, etc.): 8h jornada legal
- **LIMA**: auto-presente lun-sab sin marcar biométrico
- **NOR manual en domingo**: calcula como día normal (descanso semanal en otro día)
- **Papeletas**: APROBADA, EJECUTADA, PENDIENTE se reflejan en todos los reportes
- **Importador detalle**: cualquier marca (refrigerio/salida) sin ingreso = SS
- **Tilde FORÁNEO**: normalizar siempre (BD tiene con tilde, código sin tilde)
- **Deploy**: manual por SSH (GitHub Actions desactivado, solo workflow_dispatch)

## Pendientes
- Configurar API keys de AI (Gemini, OpenAI) en admin de ambos proyectos
- Configurar Sentry DSN para monitoreo de errores
- Gestión de usuarios: pantalla dentro del ERP (no solo admin Django)
- Subdomains por empresa: tuempresa.harmoni.pe (requiere wildcard DNS + SSL)
- Disco VPS al 81% — limpiar backups/logs viejos cuando sea necesario

## Memorias adicionales
- [Capacidad del servidor y plan de escalado](project_server_capacity.md)
- [Ciclo HE unificado 22→21](project_asistencia_ciclo_he.md) — regla + archivos que la leen
- [Sync automático Papeleta ↔ RegistroTareo](project_asistencia_sync_papeletas.md) — signals + ReglaEspecialPersonal
- [Flujo de importación mensual](project_asistencia_flujo_importacion.md) — 6 pasos en orden para nuevo ciclo
- [Reglas de cálculo de asistencia](project_asistencia_reglas_calculo.md) — SS, feriados, redondeo 0.5, compensaciones
- [Estilo de trabajo con CONSORCIO STILER](feedback_cliente_consorcio_stiler.md) — preferencias del usuario
- [Integración directa Synkro RRHH](project_synkro_integracion.md) — sync SQL Server cada 15 min + botón manual
- [Plan estabilización Q2 2026](project_plan_estabilizacion.md) — tests, Sentry, backup, turno noche antes de feature work
