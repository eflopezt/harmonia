# Bugs Resueltos Q2 2026 (abril)

**Sprint corto post-integración Synkro**

| # | Bug | Causa | Fix | Commit |
|---|-----|-------|-----|--------|
| 1 | Edición matriz no creaba papeleta | Solo era unidireccional papeleta→tareo | Auto-papeleta al editar celda | `1c0dc7a` |
| 2 | Auto-papeleta solo en celdas con registro | Otro endpoint para celdas vacías sin sync | Aplicar también en `ajax_calendario_crear` | `d4c19bf` |
| 3 | F y FA tratados distinto | Histórico, sin normalizar | Normalizar F→FA + anular papeletas huérfanas | `08d4a3c` |
| 4 | Reportes con filtro papeletas inconsistente | Solo `exportar_faltas` lo aplicaba | Helper `_qs_sin_papeleta` + autofilter Excel + hoja A-Z | `c5d144d` |
| 5 | Helper papeletas no incluía PENDIENTE | Diferencia con matriz | Incluir PENDIENTE por defecto | `4d11839` |
| 6 | Reglas especiales no retroactivas | Solo aplicaban a días nuevos | Comando `aplicar_reglas_especiales` | `57d02bb` |
| 7 | Búsqueda Reportes RRHH no encuentra "ACUNA" | `icontains` Postgres respeta tildes | Normalización NFKD case+accent insensitive | `ad77af9` |
| 8 | Reporte RCO duplicaba trabajadores | Agrupaba por `(dni, nombre_archivo, personal_id)` con espacios distintos | Solo `personal_id`, usar nombre canónico | `7e3fb86` |
| 9 | Falta columnas F.Ingreso/F.Cese en exportaciones | Pedido directo | Agregar columnas + autofilter | `8ce69e9` |
| 10 | DNI 75337871 falta seguía apareciendo en reporte | Tenía papeleta PENDIENTE | _qs_sin_papeleta incluye PENDIENTE | `4d11839` |
| 11 | Sync Synkro pisaba EXCEL del operador | EXCEL en `FUENTES_REESCRIBIBLES` | Quitar EXCEL → preservar HE manuales | `22d0cb2` |
| 12 | Sync Synkro importaba 1,441 obreros | No filtraba por TipoTrabajador | Filtrar `id_tipo_trabajador=3` (Empleado) | `f428517` |
| 13 | RegistroTareo.grupo desfasado de Personal | Denormalizado sin sync | UPDATE 449 + filtrar por `personal__grupo_tareo` | `842721b` |
| 14 | DNI con condicion FORÁNEO sin tilde inconsistente | 8,037 registros desfasados | UPDATE alinear con Personal.condicion | manual SQL |
| 15 | 14 trabajadores LOCAL marcados como FORÁNEO en regs | Personal correcto, regs incorrectos | UPDATE + recalcular HE | manual fix |
| 16 | Personal con condicion incorrecta | Operador puso LOCAL siendo FORÁNEO/LIMA | UPDATE Personal según cargo/realidad | manual fix |
| 17 | Reporte horas RCO incluía pre-altas | No filtraba por fecha_alta | Excluir registros + trabajadores fuera de período laboral | `a9a06a0` |
| 18 | sync_picados no respetaba fecha_alta/cese | Bug crítico | `if fecha < fecha_alta: continue` | `3638282` |
| 19 | Papeletas duplicadas (858) | Importaciones múltiples sin dedup | Cleanup directo BD | manual SQL |
| 20 | Papeletas traslapadas no fusionadas (67) | No había lógica de merge | Script merge automático | manual SQL |

## Lecciones aprendidas

1. **Datos denormalizados son trampa**: `grupo`, `condicion`, `dni`, `nombre_archivo` en RegistroTareo SE DESFASAN. Usar siempre `personal__campo_canonico`.
2. **Tests automatizados son urgentes**: 20 bugs en 3 días → cada fix descubrió otro bug.
3. **Idempotencia en sync**: usar markers `SYNKRO#{id}` para deduplicar entre corridas.
4. **Validación cross-reportes**: cuando los reportes dan números distintos para el mismo dato, hay bug. Test que los compare.
5. **Períodos CERRADOS son sagrados**: nunca tocar a menos que se reabran explícitamente.
6. **bulk_create no dispara signals**: documentado en memoria — siempre usar `objects.create()` o `bulk_create + comando sync`.
