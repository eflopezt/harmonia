---
name: Flujo de importación mensual de asistencia
description: Pasos en orden para cargar un nuevo ciclo (Lista_Personal + Asistencia_Detalle + PermisosLicencias)
type: project
originSessionId: 0b018c3b-3599-40f3-9b32-90e703997638
---
## Archivos estándar del cliente (exportados desde Synkro)

1. `Lista_Personal.xlsx` — hoja "Sheet", columnas: Codigo, DNI, Personal, FechaIngreso, Estado (True/False), Condicion, Cargo, FechaCese, MotivoCese, Area, Lugar Trabajo, TipoTrabajador, Partida, etc.
2. `Asistencia_Detalle_Consorcio.xlsx` — hoja "Sheet", columnas: DNI, Personal, Condicion, Fecha (DD/MM/YYYY), Ingreso, Refrigerio, FinRefrigerio, Salida (HH:MM).
3. `PermisosLicencias_Personal.xlsx` — hoja "Sheet", columnas: TipoPermiso, DNI, Personal, Area Trabajo, Cargo, Iniciales, FechaInicio, FechaFin, Detalle.

**Gotcha encoding:** los archivos vienen con caracteres `\ufffd` (reemplazo). Los comandos normalizan: FORÑEO→FORANEO, Á/É/Í/Ó/Ú/Ñ sin tilde. Siempre guardar `condicion` sin tilde.

## Secuencia correcta (ciclo mensual, ej: 22/03 → 21/04)

```bash
# 1. Actualizar personal (ceses + ingresos nuevos)
docker exec harmoni-web python manage.py sync_lista_personal /tmp/Lista_Personal.xlsx --dry-run
docker exec harmoni-web python manage.py sync_lista_personal /tmp/Lista_Personal.xlsx

# 2. Importar asistencia (con --forzar si ya hay registros previos del periodo)
docker exec harmoni-web python manage.py importar_synkro_detalle /tmp/Asistencia_Detalle_Consorcio.xlsx \
    --fecha-ini 2026-03-22 --fecha-fin 2026-04-21 --forzar

# 3. Importar papeletas (--merge preserva existentes; sin --merge borra IMPORTACION previas)
docker exec harmoni-web python manage.py importar_papeletas_excel /tmp/PermisosLicencias_Personal.xlsx \
    --fecha-ini 2026-03-22 --fecha-fin 2026-04-21 --merge

# 4. Generar faltas/DS/A_LIMA/FER para días sin marca
docker exec harmoni-web python manage.py generar_faltas_auto \
    --fecha-ini 2026-03-22 --fecha-fin 2026-04-21

# 5. Aplicar compensaciones de feriados (si el período tiene feriados con compensación)
# Ej. Semana Santa:
docker exec harmoni-web python manage.py aplicar_feriados_semana_santa_2026

# 6. (opcional) Reconciliar papeletas con registros si se hizo bulk ops
docker exec harmoni-web python manage.py sync_papeletas_registros \
    --fecha-ini 2026-03-22 --fecha-fin 2026-04-21
```

**Why orden:** Personal debe existir antes de asistencia (matcheo por DNI). Papeletas antes de `generar_faltas_auto` para que respete los días cubiertos. Compensaciones al final porque tocan registros ya generados.

**How to apply:** Los signals automáticos cubren cambios posteriores a mano en el ERP (admin crea papeleta → sync automático). Los comandos 4-6 solo se corren tras importaciones bulk.

## Reglas de jornada

- **LOCAL/LIMA**: L-V 8.5h, Sáb 5.5h, Dom 0h (si trabaja → 100% HE)
- **FORÁNEO**: L-S 10h (efectiva sin almuerzo), Dom 4h (parte del ciclo 21×7)
- Almuerzo descontado: 1h si raw > 7h
- Feriado laborado: TODO al 100% HE (D.Leg 713)

## Correcciones históricas aplicadas (abril 2026)

Commits clave en orden:
- `1be0c02` — PDF área report
- `8929f0f` — Redondeo horas a múltiplo de 0.5 (4063 registros)
- `16bfbef` — Fix 361 inconsistencias (P1 01-ene feriado, P2 ent=sal, P3 dom 22-mar, P4 norm>ef → SS jornada)
- `1443044` — Unificar ciclo HE 22→21 en todo (banco, dashboard, staff, exportaciones, reprocesar)
- `41d79db` — SS en feriado laborado va a HE100
- `7e0a693` — Comando generar_faltas_auto
- `ee16f57` — Compensaciones Semana Santa (CPF)
- `c41f242` — Signals auto-sync Papeleta ↔ RegistroTareo
- `927e9d6` — Compensación 02→04 abril para TODOS (no solo FORÁNEO)
- `b9ac20d` — ReglaEspecialPersonal integrada en _codigo_default
- `03ee8f6` — Modo --merge en importar_papeletas_excel
