# Deuda Técnica Harmoni — Lista priorizada

**Última revisión:** 2026-04-29

## Severidad

- 🔴 Crítico — bloqueante para feature work
- 🟡 Alto — costo creciente si no se atiende
- 🟢 Medio — mejorable cuando se pueda

## Items

### 🔴 Tests automatizados

**Costo actual:** cada cambio requiere prueba manual extensa. Bugs en cascada.
**Costo no-action:** crece exponencialmente con features nuevas.
**Esfuerzo:** 5-7 días para cobertura mínima 60% en módulos críticos.

### 🔴 Datos denormalizados sin sync

**Hoy:** RegistroTareo guarda `grupo, condicion, dni, nombre_archivo` que pueden desincronizarse de Personal.
**Riesgo:** filtros por estos campos dan resultados erróneos.
**Mitigación parcial:** views ya cambiaron a `personal__campo_canonico`.
**Solución completa:**
- Opción A: signal `pre_save Personal` que sincroniza campos en RegistroTareo asociados.
- Opción B: borrar los denormalizados (`grupo`, `condicion`, `dni`, `nombre_archivo`) y migrar todo el código a usar FK.

Opción B es más limpia. Esfuerzo: 2-3 días + migración cuidadosa.

### 🔴 Cálculo HE disperso en 4-5 archivos

**Hoy:** lógica vive en `processor.py`, `_recalcular_horas` (en views/calendario), `kpis.py`, `exportaciones.py`, `synkro_sync.py`.
**Riesgo:** cambio en regla → toca varios lugares → desincronía.
**Solución:** módulo `services/he_calculator.py` con función pura. Resto consume.
**Esfuerzo:** 3-4 días con tests.

### 🟡 Períodos CERRADOS no protegidos uniformemente

**Hoy:** algunos endpoints validan `fecha_en_periodo_cerrado()`, otros no.
**Lugares vulnerables:** Django admin, comandos management ad-hoc, scripts que tocan BD directo.
**Solución:** signal `pre_save RegistroTareo` que rechaza modificación si está en período CERRADO (excepto reapertura explícita).

### 🟡 Auditoría de cambios

**Hoy:** `CambioCodigoLog` solo cubre matriz asistencial.
**Falta:** ediciones via Django admin, importaciones, sync Synkro auto, ediciones en panel papeletas.
**Solución:** `django-simple-history` o tabla audit propia + middleware.

### 🟡 Backup automatizado

**Hoy:** sin backup programado.
**Riesgo:** fallo de disco = pérdida total.
**Solución:** cron `pg_dump | gzip | aws s3 cp` diario. ~5 USD/mes.

### 🟡 Sin alertas Sentry

**Hoy:** `SENTRY_DSN` vacío en `.env.production`.
**Riesgo:** errores silenciosos.
**Solución:** crear cuenta Sentry free tier, configurar DSN, agregar wraps en tasks Celery críticos.

### 🟡 Falta de estandarización en `condicion`

**Hoy:** valores `LOCAL`, `LIMA`, `FORANEO`, `FORÁNEO` (con/sin tilde) coexisten.
**Mitigación parcial:** `_cond_norm()` normaliza en sync, processor.py ya maneja ambos.
**Solución:** UPDATE masivo a `FORANEO` (sin tilde) + constraint `CHECK (condicion IN ('LOCAL', 'LIMA', 'FORANEO'))`.

### 🟢 Performance escalabilidad

**Hoy:** 854K picados / 200 empleados / 4 meses.
**Proyección:** 6.5M picados/año a 200 empleados. A 500 empleados → 16M/año.
**Mitigación:**
- Particionar `RegistroTareo` por mes (PostgreSQL native partitioning).
- Índices funcionales sobre `(personal_id, fecha)` y `(grupo, fecha)`.
- Materialized views para dashboards KPIs (refresh nocturno).

### 🟢 Roles y permisos finos

**Hoy:** binario admin/no-admin.
**Necesidades:** roles para nómina, RRHH, supervisor obra, capataz, gerencia (cada uno con scope distinto).
**Solución:** Django groups + permission per app.

### 🟢 Documentación reglas peruanas centralizada

**Hoy:** dispersa entre código + memoria Claude.
**Solución:** `docs/internal/REGLAS_NEGOCIO_*.md` por dominio.

### 🟢 Health check del sync Synkro

**Hoy:** solo `health_check_papeletas` corre 5:30am.
**Falta:** verificar que sync Synkro corrió en último período, métricas básicas (cantidad de picados nuevos por día).
**Solución:** management command + alerta Slack si no corrió en últimas 2 horas.

### 🟢 Migración a tipos canónicos en motivo_cese

**Hoy:** synkro guarda string libre, mapeo defensivo.
**Solución:** UI form con dropdown directo en Personal admin.
