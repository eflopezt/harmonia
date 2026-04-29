---
name: Ciclo HE unificado 22→21
description: Regla del ciclo de planilla (día 22 del mes anterior al 21 del actual) y dónde se lee en el código
type: project
originSessionId: 0b018c3b-3599-40f3-9b32-90e703997638
---
## Regla

`ConfiguracionSistema.dia_corte_planilla` (=21) define el ciclo HE:
- ciclo = **(corte+1) del mes anterior → corte del mes actual**
- Con corte=21 → ciclo abril 2026 = 22/mar/2026 → 21/abr/2026

**Why:** El usuario pidió explícitamente que TODOS los reportes usen 22→21. El commit `e34ca45` migró calendario.py y reporte_individual.py pero quedaron 5 archivos hardcoded 21→20 que se corrigieron en commit `1443044`.

**How to apply:** Nunca hardcodear 21 o 20 en lógica de rangos. Siempre usar `ConfiguracionSistema.get_ciclo_he(anio, mes)` o leer `config.dia_corte_planilla`. Si necesitas fallback, usar `corte+1` para inicio y `corte` para fin.

## Archivos que leen el ciclo

- `asistencia/views/banco.py::_get_ciclo` → `config.get_ciclo_he()`
- `asistencia/views/reporte_individual.py::_get_ciclo` → ídem
- `asistencia/views/calendario.py` → ídem
- `asistencia/views/dashboard.py` → ídem
- `asistencia/views/staff.py` → ídem
- `asistencia/views/exportaciones.py::_get_corte_config` → `(corte+1, corte)`
- `asistencia/services/reprocesar_personal.py` → ídem

Templates alineados (22-21):
- `templates/nominas/periodo_form.html` (texto legal + JS autofill)
- `templates/nominas/registro_editar.html`
