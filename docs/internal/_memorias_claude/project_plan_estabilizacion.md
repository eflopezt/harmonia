---
name: Plan estabilización Harmoni Q2 2026
description: Hoja de ruta priorizada para llevar Harmoni a producción robusta antes de feature work
type: project
originSessionId: 14421100-76fd-4e94-bb4c-a0c61db61e98
---
## Decisión 2026-04-29
**Antes de feature nuevo, estabilizar.** El sprint corto post-Synkro evidenció que cada cambio descubre otro bug en cascada. Sin tests automatizados, refactorizar es riesgoso.

**Why:** 20+ bugs detectados y arreglados en 3 días post-integración Synkro (commits abril 27-29). Datos denormalizados desfasados, importes Excel pisados, papeletas duplicadas, condiciones LOCAL/FORÁNEO mal asignadas, turnos noche mal procesados, sync incluyendo obreros. Cada fix descubría más.

**How to apply:** Cuando el user pida feature nueva en mayo 2026, recordar esta decisión y proponer terminar primero los items críticos (tests + Sentry + backup + turno noche).

## Prioridades

### 🔴 Críticas (próximas 2 semanas)
1. **Tests automatizados** cálculo HE + sync Synkro (60% coverage mínimo). Ubicación: `asistencia/tests/`, `integraciones/tests/`. Usar pytest-django + factory_boy.
2. **Turno noche en sync_picados**: regla "picados <5:30am son salida del día anterior, salida puede pasar medianoche hasta 5:00 día siguiente". Ya validado con caso DNI 70919188 (LOPEZ TORRE) en Excel manual; falta llevar a producción.
3. **Sentry DSN + alertas Celery**. Cuenta free tier (5k errores/mes). DSN vacío en `.env.production`. Wraps en `sync_synkro_auto`, `health_check_papeletas`.

### 🟡 Importantes (mayo)
4. Limpieza 1,008 RegistroTareo legacy en períodos CERRADOS (condicion desfasada).
5. Audit log completo (no solo `CambioCodigoLog`).
6. Backup automatizado pg_dump → S3/B2 (~5 USD/mes).
7. Refactor `services/he_calculator.py` único.

### 🟢 No bloqueantes
8. Performance escalabilidad (índices, particionado).
9. Documentación reglas peruanas centralizada.
10. Roles/permisos finos.

## Cronograma sugerido
- Sem 1: Sentry + backup + tests cálculo HE
- Sem 2: Tests sync Synkro + turno noche en producción
- Sem 3: Limpieza legacy + audit log
- Sem 4: Refactor he_calculator + docs
- Cierre mayo: planilla con sistema estable

## Métricas para "estable"
- Coverage ≥60% en módulos críticos
- 0 errores Sentry abiertos > 1 día
- Backup verificado (restore mensual de prueba)
- 0 inconsistencias matriz/PDF/Excel para mismo dato
- 0 registros denormalizados desfasados (audit diario)
- Turno noche correcto en 100% casos prueba

## Documentación complementaria
- `docs/internal/PLAN_ESTABILIZACION_2026.md` — versión extensa para equipo
- `docs/internal/BUGS_RESUELTOS_2026-Q2.md` — registro de los 20 bugs
- `docs/internal/DEUDA_TECNICA.md` — items priorizados

## Riesgos si no estabilizamos
- **Cierre mayo en riesgo**: sin tests, regresiones probables.
- **Vender a otras empresas con bugs**: daña reputación.
- **Crece deuda exponencialmente**: cada feature suma sin base sólida.
