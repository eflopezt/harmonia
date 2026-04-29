---
name: Estilo de trabajo con el cliente CONSORCIO STILER
description: Preferencias del usuario sobre cómo proceder en el módulo de asistencia/nómina
type: feedback
originSessionId: 0b018c3b-3599-40f3-9b32-90e703997638
---
El usuario es administrador del ERP Harmoni para CONSORCIO STILER (229 empleados activos al 2026-04). Pide cambios directos en producción (no hay staging), con iteraciones frecuentes.

## Reglas de trabajo confirmadas

1. **Ciclo de planilla 22→21** (día del mes 22 al 21 del siguiente), NO 21→20 que era el hardcoded legacy.
   **Why:** El cliente definió este corte. Config: `ConfiguracionSistema.dia_corte_planilla=21`.
   **How to apply:** Nunca hardcodear 21/20 en reportes. Siempre leer de config.

2. **Todas las horas redondeadas a múltiplo de 0.5** (ROUND_HALF_UP).
   **Why:** Exigencia del cliente, evita fracciones de minuto en planilla.
   **How to apply:** `horas_marcadas` queda bruto; el resto (ef/norm/HE25/35/100) se redondea.

3. **FA vs FER vs TR**: feriado no laborado debe ser FER (no FA). Días sin marca de empleados específicos (5 DNIs) deben ser TR (trabajo remoto). Nunca mostrar "falta" cuando no es una falta real.
   **Why:** El usuario preguntó "por qué sale falta si es feriado" y "por qué sale falta si tienen papeleta CHE". Para él las faltas deben ser solo casos reales de no asistencia injustificada.
   **How to apply:** Usar `_codigo_default()` que evalúa feriados → FER, dom LOCAL → DS, LIMA → A, reglas especiales → override.

4. **Sync automático siempre**: cambios en papeletas deben reflejarse instantáneamente en todos los reportes.
   **Why:** Cita literal: "debe ser de todos y automatico siempre en todo".
   **How to apply:** Signals `post_save`/`post_delete` en `RegistroPapeleta`. Nunca usar `bulk_create` sin ejecutar `sync_papeletas_registros` después.

5. **Puede tocar periodos cerrados**: cuando pide correcciones de data histórica, proceder sin pedir confirmación adicional.
   **Why:** Cita: "puedes tocar periodos cerrados, corrige todo 2026".
   **How to apply:** No preguntar "¿estás seguro?" en fixes retroactivos del 2026. Sí confirmar cambios que afecten otros años.

6. **Compensaciones Semana Santa aplican a TODOS** los que trabajaron el feriado, no solo FORÁNEO.
   **Why:** Corrigió explícitamente mi primera implementación que filtraba solo FORÁNEO.
   **How to apply:** 02/04 → 04/04 para ambas condiciones. 03/04 → 05/04+12/04 solo FORÁNEO (LOCAL ya tiene DS los domingos).

7. **Verificación completa**: cuando pide "revisa con cuidado" o "analizado con calma y precisión", validar cada caso con ejemplos concretos antes de aplicar.
   **Why:** Cita: "revisalo con cuidado, analizado con todo lo aprendido y configurado etc".
   **How to apply:** Dry-run antes de aplicar. Mostrar muestra de registros afectados. Contrastar totales.

8. **No crear papeletas masivas sin merge**. El archivo de papeletas suele ser delta (solo nuevas).
   **Why:** Al cargar el delta en modo "reemplazar", se borran todas las manuales previas.
   **How to apply:** Usar `importar_papeletas_excel --merge` para archivos incrementales.

## Estilo de comunicación

- Responde en español.
- Le gusta el detalle técnico (commits hash, conteos exactos, tabla por casos).
- Reporta verificaciones después de aplicar ("FERMIN ahora tiene... antes: X / ahora: Y").
- Cuando detecta un bug, muestra un caso específico (screenshot de Asistencia Matricial) — usarlo como punto de partida, luego buscar patrón general.

## Despliegue

- No hay CI. Push a GitHub → `sudo git pull` en VPS → `sudo docker restart harmoni-web` (y celery/beat si aplica).
- Scripts de reparación se copian via `scp` a `/tmp/` → `docker cp` al container si es necesario.
- Puede haber conflictos locales en git pull si se copiaron archivos directos antes del commit: usar `sudo git checkout <archivo>` o `sudo rm <archivo>` para limpiar antes del pull.
