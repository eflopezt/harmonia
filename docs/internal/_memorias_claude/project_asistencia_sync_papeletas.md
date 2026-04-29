---
name: Sync automático Papeleta ↔ RegistroTareo
description: Arquitectura del signal-based sync entre RegistroPapeleta y RegistroTareo, incluye ReglaEspecialPersonal
type: project
originSessionId: 0b018c3b-3599-40f3-9b32-90e703997638
---
## Arquitectura

`asistencia/services/papeletas_sync.py` centraliza la lógica:
- `aplicar_papeleta(pap)` — propaga código derivado de tipo_permiso a los días cubiertos
- `revertir_papeleta(pap)` — restaura días al default cuando se rechaza/borra
- `_codigo_default(personal, fecha, es_feriado)` — calcula default del día (consulta ReglaEspecialPersonal)

`asistencia/signals.py` engancha vía `post_save` / `post_delete` / `pre_save` en `tareo.RegistroPapeleta`:
- APROBADA/EJECUTADA → `aplicar_papeleta()`
- PENDIENTE/RECHAZADA/ANULADA → `revertir_papeleta()`
- Cambio de rango/tipo: revierte rango viejo (snapshot en pre_save) + aplica nuevo
- Delete → revierte

**Why:** Antes había que correr comandos manuales. El usuario pidió explícitamente "debe ser de todos y automático siempre en todo". El sync in-code es la única forma segura cuando el admin crea papeletas en el ERP.

**How to apply:** NO usar `bulk_create` para RegistroPapeleta (no dispara signals). Usar `objects.create()` o `get_or_create()`. Si usas bulk, ejecutar `sync_papeletas_registros` después.

## Jerarquía de prioridad (codigo_dia)

1. **Trabajo real** — RELOJ con `ef>0` o fuente `MANUAL` → nunca se sobrescribe
2. **Papeleta aprobada** — propaga código derivado de `tipo_permiso`
3. **ReglaEspecialPersonal** activa (match dias_semana / condicion / codigo_reloj_trigger)
4. **Default calendario** — FER (feriado) > DS (dom LOCAL/LIMA) > A_LIMA (LIMA L-S) > FA

## Mapeo tipo_permiso → codigo_dia

```python
TIPO_A_CODIGO = {
    'BAJADAS': 'DL', 'BAJADAS_ACUMULADAS': 'DLA',
    'VACACIONES': 'VAC', 'DESCANSO_MEDICO': 'DM',
    'COMPENSACION_HE': 'CHE',
    'LICENCIA_CON_GOCE': 'LCG', 'LICENCIA_SIN_GOCE': 'LSG',
    'LICENCIA_FALLECIMIENTO': 'LF',
    'LICENCIA_PATERNIDAD': 'LP', 'LICENCIA_MATERNIDAD': 'LM',
    'COMISION_TRABAJO': 'CT', 'TRABAJO_REMOTO': 'CT',
    'COMPENSACION_FERIADO': 'CPF', 'COMP_DIA_TRABAJO': 'CDT',
    'SUSPENSION': 'SUS', 'SUSPENSION_ACTO_INSEGURO': 'SAI',
    'CAPACITACION': 'CAP', 'OTRO': 'OTR',
}
```

## ReglaEspecialPersonal

Modelo `asistencia.models.ReglaEspecialPersonal` para overrides automáticos por empleado. Evaluado en `_codigo_default()`:
- `codigo_reloj_trigger='FA'` → "si el default iba a ser FA, aplicar `codigo_resultado`"
- Campos filtro: `dias_semana`, `condicion_laboral`, `solo_feriados`, `fecha_desde`/`hasta`, `prioridad`, `activa`

Ej: 5 DNIs tienen regla FA→TR (trabajo remoto):
- 005892606 CANIZA VIERCI
- 005835751 CASTILLO AQUINO
- 007453650 CUELLAR TERAN
- 005419022 GUTIERREZ FERRER
- 001526140 MESTRE SALORT

## Sync inverso: matriz → papeleta (2026-04-27)

`papeletas_sync.crear_papeleta_desde_codigo(personal, fecha, codigo, usuario, observacion)` crea papeleta APROBADA de un día desde un `codigo_dia` de `RegistroTareo`. Usa el mapeo inverso `CODIGO_A_TIPO` (excluye códigos de presencia/falta).

Disparado desde `ajax_calendario_cambiar` (matriz asistencial): cuando el admin edita una celda y pone VAC/DM/DL/LCG/CHE/CPF/CDT/SUS/SAI/CAP/CT/etc., se crea `RegistroPapeleta(origen=SISTEMA, estado=APROBADA, dias_habiles=1)` y el `RegistroTareo` queda con `fuente_codigo='PAPELETA'` + `papeleta_ref='PAP#{id}'`. Si ya hay papeleta cubriendo el día con el mismo tipo, se reutiliza (no duplica).

**Why:** El usuario pidió que la edición directa en la matriz también genere papeleta, para que descuente saldos (vacaciones) y aparezca en reportes de permisos.

**How to apply:** El signal `aplicar_papeleta` skipea días con `fuente_codigo='MANUAL'`, por eso el view setea PAPELETA + papeleta_ref manualmente tras crear la papeleta.

## Comandos relacionados

- `generar_faltas_auto --fecha-ini X --fecha-fin Y` — crea FA/DS/A_LIMA/FER en días sin marca ni papeleta. Usa `_codigo_default()`, respeta reglas especiales.
- `sync_papeletas_registros [--fecha-ini X --fecha-fin Y]` — reconciliación masiva (útil tras bulk ops que no disparan signals).
- `backfill_papeletas_desde_tareo [--fecha-ini X --fecha-fin Y] [--personal ID] [--dry-run]` — crea papeletas faltantes para `RegistroTareo` cuyo código está en `CODIGO_A_TIPO` pero sin papeleta asociada. Agrupa días consecutivos del mismo personal+codigo en una sola papeleta. Omite períodos CERRADOS.
- `aplicar_feriados_semana_santa_2026` — caso puntual 2026.
