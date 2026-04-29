# Backup de Memorias Claude

Snapshot de las memorias de Claude Code para Harmoni.

**Origen local:** `C:\Users\EDWIN LOPEZ\.claude\projects\D--Harmoni\memory\`

**Última sincronización:** 2026-04-29

## Para qué sirve

Si Edwin (o quien continúe) trabaja desde otra laptop y no tiene acceso a su PC habitual, puede:
1. Clonar este repo
2. Copiar `_memorias_claude/*.md` → `~/.claude/projects/D--Harmoni/memory/` (o ruta equivalente en macOS/Linux)
3. Claude Code retoma con todo el contexto histórico

## Cómo mantener actualizado

Cuando vuelvas a tu PC habitual y agregues nuevas memorias, ejecuta desde `D:\Harmoni\`:

```bash
cp "/c/Users/EDWIN LOPEZ/.claude/projects/D--Harmoni/memory/"*.md docs/internal/_memorias_claude/
git add docs/internal/_memorias_claude/
git commit -m "sync memorias claude $(date +%Y-%m-%d)"
git push
```

O pídele a Claude que lo haga: *"sincroniza las memorias a github"*.

## Contenido

- `MEMORY.md` — índice principal
- `project_*.md` — memorias de proyecto
- `feedback_*.md` — feedback del cliente

## ⚠️ NO subir aquí

Si hay memorias con secretos (claves, contraseñas, datos personales), NO subirlas. En su lugar:
- Mover al servidor `/opt/harmoni/secrets/`
- Eliminar antes de hacer commit
