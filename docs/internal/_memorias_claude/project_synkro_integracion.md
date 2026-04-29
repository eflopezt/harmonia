---
name: Integración directa Synkro RRHH (SQL Server)
description: Sync directo desde la BD del biométrico Synkro (SistemaRRHHCSRT) hacia Harmoni — auto cada 15 min + botón manual
type: project
originSessionId: 14421100-76fd-4e94-bb4c-a0c61db61e98
---
## Contexto
Synkro/SistemaRRHHCSRT es el sistema de control de personal y asistencia biométrica que CONSORCIO STILER ya tenía cuando se implementó Harmoni. Antes se importaba vía Excel manual. Desde 2026-04-28 hay sync directo a la BD remota.

## Conectividad
- **SQL Server**: `161.132.56.202\SQLEXPRESS:1433`
- **DB**: `DB_RRHH` | usuario `rrhh` / `Csrt@2025`
- **El VPS Harmoni (212.56.34.166) llega TCP directo** al puerto 1433 — por eso se eligió integración directa en vez de agente local.
- Credenciales se extrajeron de `Datos.dll` del SistemaRRHHCSRT instalado vía ClickOnce (`AppData\Local\Apps\2.0\...\Datos.dll`). El password está hardcodeado en la DLL sin ofuscar.

## Configuración env vars
En `/opt/harmoni/app/.env.production`:
```
SYNKRO_HOST=161.132.56.202\SQLEXPRESS
SYNKRO_PORT=1433
SYNKRO_DB=DB_RRHH
SYNKRO_USER=rrhh
SYNKRO_PASSWORD=Csrt@2025
SYNKRO_DRIVER=ODBC Driver 18 for SQL Server
```
Si `SYNKRO_HOST` no está, la DB secundaria no se registra y el sync hace no-op.

## Arquitectura
- **DB secundaria 'synkro'** (read-only) en `config/settings/production.py`. mssql-django + pyodbc + msodbcsql18 (Dockerfile).
- **Modelos unmanaged** en `integraciones/synkro_models.py`: `PerPersona`, `PPersonal`, `PicadoPersonal`, `TipoPermiso`, `PermisoLicencia`, `FeriadoSynkro`.
- **Modelo managed** `integraciones.SyncSynkroLog` para audit + cursor incremental.
- **Servicio** `integraciones/services/synkro_sync.py`: orquesta feriados → papeletas → picados.

## Reglas de sync
- **Match key**: `PER_Personas.Dni` ↔ `Personal.nro_doc` (sin lpad).
- **Picados → RegistroTareo**: agrupa por (personal, fecha), entrada=MIN, salida=MAX. Si solo hay 1 picado → SS.
- **Solo sobrescribe** registros con `fuente_codigo` en `{FALTA_AUTO, DESCANSO_SEMANAL, AUTO_LIMA, REGLA_ESPECIAL, FERIADO, EXCEL, RELOJ}`. Respeta `MANUAL` y `PAPELETA con papeleta_ref`.
- **Períodos CERRADOS**: nunca se modifican.
- **Idempotente**: papeletas se identifican por `observaciones LIKE 'SYNKRO#{IdPermiso}%'` para evitar duplicados.
- **Cursor incremental**: tomado del último log OK (`SyncSynkroLog.cursor_papeletas` y `cursor_picados`). Reset con `--reset-cursor`.

## Mapeo TipoPermiso (Synkro → Harmoni)
1=DESCANSO_MEDICO · 2=LICENCIA_CON_GOCE · 3=LICENCIA_SIN_GOCE · 4=VACACIONES · 5=LICENCIA_PATERNIDAD · 6=BAJADAS · 7=TRABAJO_REMOTO · 8=COMISION_TRABAJO · 9=SUSPENSION_ACTO_INSEGURO · 10=LICENCIA_FALLECIMIENTO · 11=OTRO (ATM) · 12=COMP_DIA_TRABAJO · 13=SUSPENSION (AS) · 14=BAJADAS_ACUMULADAS · 15=None (FR ignorado) · 16=COMPENSACION_HE · 17=COMPENSACION_FERIADO

## Disparadores
- **Auto**: Celery Beat `'sync-synkro-rrhh-15min'` cada 15 min — tarea `integraciones.tasks.sync_synkro_auto` (ventana picados=7 días).
- **Manual**: botón "Sincronizar ahora" en `templates/asistencia/importar.html` → POST `/integraciones/synkro/sync-now/` → tarea Celery `sync_synkro_manual` (ventana=60 días).
- **CLI**: `python manage.py sync_synkro [--dry-run|--reset-cursor|--ventana-dias N]`.

## Volumen actual
- 854K picados desde 2025-01 a hoy. Sync incremental procesa pocos por corrida (<100 ms cada query típica con índice en Fecha).
- 17 tipos de permiso. Feriados: pocas decenas.

## Tablas relevantes en Synkro
- `PER_Personas` (Dni, APaterno, AMaterno, Nombres, NombreCompleto, Celular, Correo) — match por DNI.
- `P_Personal` (IdPersonal, IdPersona, Estado, FechaIngreso, FechaTerminoContrato, MotivoCese, Codigo).
- `PicadosPersonal` (IdPicado, IdPersonal, Fecha datetime, HoraPicado int seg-desde-medianoche, FechaSinMS date, IdTipo).
- `PermisosLicencias` (IdPermiso, IdPersonal, IdTipoPermiso, FechaInicio, FechaFin, Detalle, FechaRegistro, FechaModifica).
- `TiposPermiso` (catálogo).
- `Feriados` (Fecha, Descripcion).

**Why:** El usuario tenía Synkro corriendo en su máquina y pidió integración directa para no depender de exports Excel manuales.

**How to apply:** Si el sync da datos raros, primero verificar logs en `SyncSynkroLog` (`/admin/integraciones/syncsynkrolog/`). Si hay desfase masivo → `python manage.py sync_synkro --reset-cursor --ventana-dias 90`.
