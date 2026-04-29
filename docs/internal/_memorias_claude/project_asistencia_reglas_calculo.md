---
name: Reglas de cálculo de asistencia (SS, feriados, redondeo, compensaciones)
description: Reglas críticas para que RegistroTareo refleje horas correctamente y pasen consistencia
type: project
originSessionId: 0b018c3b-3599-40f3-9b32-90e703997638
---
## Regla de redondeo a 0.5

`asistencia/services/processor.redondear_media_hora()` usa ROUND_HALF_UP a múltiplo de 0.5:
- 0.78 → 1.0, 0.62 → 0.5, 1.28 → 1.5, 0.42 → 0.5, 0.18 → 0.0, 1.25 → 1.5 (empate → up)

**Aplica a:** `horas_efectivas`, `horas_normales`, `he_25`, `he_35`, `he_100`. **NO aplica** a `horas_marcadas` (bruto del reloj).

`processor._calcular_horas` es wrapper que redondea cada componente del tuple. Si haces bulk sin pasar por el processor, usar el comando `redondear_horas_media` después.

## Invariante post-redondeo

`horas_efectivas = horas_normales + he_25 + he_35 + he_100` (tolerancia 0.01). Verificado en dataset abril 2026: redondeo independiente preserva la identidad en los casos testeados.

## Reglas SS (Sin Salida)

- **Día normal**: marcó entrada, no salida → ef = norm = jornada del día, HE = 0, codigo = SS.
- **SS en feriado**: ef = h100 = jornada, norm = 0 (regla D.Leg 713). Corregido en `importar_synkro_detalle._calcular_horas` (commit 41d79db).
- **SS en dom LOCAL**: igual que feriado (todo HE100).
- **Marcación incompleta** (<jornada/2): SS implícito → se paga jornada completa.

## Reglas feriados

- Feriado **laborado**: todas las horas → HE100 (`horas_normales=0, h100=ef`).
- Feriado **no laborado**: `codigo_dia='FER'`, ef=0, norm=0, HE=0. **NO es FA**.
- `es_feriado=True` se lee de `FeriadoCalendario.filter(activo=True)`.
- **CompensacionFeriado** se usa para trasladar feriados a otro día (ej. 15 ago → siguiente lunes). **Evitar activarlas globalmente** — causan que `es_feriado=False` en el día original y `=True` en el compensado para todos. Si una persona trabajó el feriado original, pierde los HE100. Mejor usar papeletas CPF por empleado.

## Compensaciones Semana Santa 2026

Regla del cliente (CONSORCIO STILER):
- **02/04 Jueves Santo** trabajado → compensa **04/04 Sábado** (LOCAL + FORÁNEO)
- **03/04 Viernes Santo** trabajado → compensa **05/04 Dom + 12/04 Dom** (solo FORÁNEO)
  - LOCAL que trabajó 03/04 ya recibe HE100 ese mismo día; sus domingos son DS de por sí.
- Si el día compensado también se trabajó, se respeta (A/SS con pago normal del día).
- Codigo resultado: **CPF** (Compensación Feriado), ef=0, HE=0 (día pagado en planilla).

## Descuento automático de almuerzo

**Decisión de negocio del cliente** (no legal, no laboral): si un trabajador
marca >7h y la jornada del día es >6h, se descuenta 1h por refrigerio.

- **Why**: criterio práctico — nadie trabaja tantas horas seguidas sin comer.
- **Excepciones automáticas**: jornadas cortas (sábado LOCAL 5.5h, domingo) NO
  descuentan, porque ahí no aplica hora de almuerzo.
- **Override manual**: setear `RegistroTareo.almuerzo_manual` en BD (0 para que
  no descuente, otro valor para forzar otro descuento). Tiene prioridad absoluta.
- **How to apply**: cualquier nuevo path de cálculo de horas debe usar el helper
  `asistencia.services._helpers.calcular_almuerzo_h()` para mantener consistencia
  entre import (processor) y edición manual (UI calendar).

## Reglas de default (día sin marca ni papeleta)

`_codigo_default()` en `papeletas_sync.py`:
1. Si es feriado → FER
2. Dom LOCAL/LIMA → DS
3. LIMA L-S → A (auto-presente)
4. Resto (FORÁNEO L-D, LOCAL L-S) → FA
5. **Sobre esto aplica ReglaEspecialPersonal** si hay match

## Gotchas conocidos

- **FORÁNEO con tilde** en BD es inconsistente. El código mayormente normaliza con `.upper().replace('Á','A')`. 16 cesados tenían con tilde, normalizados en commit post-correcciones. Siempre normalizar al guardar.
- **dia_semana**: 0=Lun ... 6=Dom (Python `weekday()`).
- **Abril 2026** tenía spike HE100 (6450h vs 930h en marzo) — NO es bug: son Jueves/Viernes Santo laborados.
- **Personal.estado** es `'Activo'` / `'Cesado'` (capitalizado), NO `'ACTIVO'`.
- **Personal.condicion** vacío cuenta como LOCAL por defecto.

## Comandos de reparación

- `redondear_horas_media [--dry-run]` — redondea campos que no sean múltiplo de 0.5. Usa `MOD(x*10, 5)` (NO `::int`, que trunca).
- `fix_inconsistencias_horas --dry-run` — 4 patrones: P1 feriado 01-ene, P2 ent=sal, P3 dom 22-mar, P4 norm>ef.
- `aplicar_feriados_semana_santa_2026` — idempotente, FA→FER en feriados + FA→CPF en compensaciones.
