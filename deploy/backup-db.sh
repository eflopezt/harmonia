#!/usr/bin/env bash
# =============================================================================
# PostgreSQL Backup — Harmoni ERP
# Uso: crontab -e → 0 2 * * * /opt/harmoni/app/deploy/backup-db.sh
# Mantiene 7 días de backups
# =============================================================================
set -euo pipefail

BACKUP_DIR="/opt/harmoni/backups"
DATE=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=7

mkdir -p "$BACKUP_DIR"

# Backup Harmoni
echo "[$(date)] Backing up harmoni_db..."
pg_dump -U harmoni -h 127.0.0.1 harmoni_db | gzip > "${BACKUP_DIR}/harmoni_db_${DATE}.sql.gz"

# Backup NexoTalent
echo "[$(date)] Backing up nexotalent_db..."
pg_dump -U nexotalent -h 127.0.0.1 nexotalent_db | gzip > "${BACKUP_DIR}/nexotalent_db_${DATE}.sql.gz"

# Limpiar backups antiguos
echo "[$(date)] Cleaning backups older than ${RETENTION_DAYS} days..."
find "$BACKUP_DIR" -name "*.sql.gz" -mtime +${RETENTION_DAYS} -delete

# Mostrar espacio usado
echo "[$(date)] Backup complete. Space used:"
du -sh "$BACKUP_DIR"
ls -lh "$BACKUP_DIR"/*.sql.gz | tail -5
