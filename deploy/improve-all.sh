#!/bin/bash
set -euo pipefail
exec > /root/improve.log 2>&1

echo "=== $(date) — Starting improvements ==="

# ── 1. Fix Harmoni beat (celery_beat app missing) ──
echo "[1/6] Rebuilding Harmoni..."
cd /opt/harmoni/app
COMPOSE_PROJECT_NAME=harmoni docker compose -f docker-compose.prod.yml down
COMPOSE_PROJECT_NAME=harmoni docker compose -f docker-compose.prod.yml build web
COMPOSE_PROJECT_NAME=harmoni docker compose -f docker-compose.prod.yml run --rm web python manage.py migrate --noinput
COMPOSE_PROJECT_NAME=harmoni docker compose -f docker-compose.prod.yml run --rm -v /opt/harmoni/staticfiles:/app/staticfiles web python manage.py collectstatic --noinput
chown -R 777 /opt/harmoni/staticfiles
COMPOSE_PROJECT_NAME=harmoni docker compose -f docker-compose.prod.yml up -d
sleep 20
echo "  Harmoni rebuild OK"

# ── 2. Run NexoTalent seeds ──
echo "[2/6] Running NexoTalent seeds..."
cd /opt/nexotalent/app
docker exec nexotalent-web python manage.py migrate --noinput 2>&1 | tail -5
docker exec nexotalent-web python manage.py collectstatic --noinput 2>&1 | tail -1
docker exec nexotalent-web python manage.py createsuperuser --username admin --email eflopezt@gmail.com --noinput 2>&1 || echo "  superuser exists"
docker exec nexotalent-web python manage.py shell -c "
from django.contrib.auth.models import User
u = User.objects.get(username='admin')
u.set_password('admin123')
u.save()
print('Admin password set')
" 2>&1
echo "  NexoTalent seeds OK"

# ── 3. Install OpenClaw ──
echo "[3/6] Installing OpenClaw..."
npm install -g clawdbot@latest 2>&1 | tail -5 || echo "  OpenClaw install error, continuing..."
mkdir -p /opt/openclaw/data
chown -R deploy:deploy /opt/openclaw

# Create systemd service
cat > /etc/systemd/system/openclaw.service << 'SVCEOF'
[Unit]
Description=OpenClaw AI Assistant
After=network.target

[Service]
Type=simple
User=deploy
WorkingDirectory=/opt/openclaw
ExecStart=/usr/bin/npx clawdbot start
Restart=always
RestartSec=10
Environment=NODE_ENV=production
Environment=HOME=/home/deploy

[Install]
WantedBy=multi-user.target
SVCEOF
systemctl daemon-reload
systemctl enable openclaw
echo "  OpenClaw service created (run 'openclaw onboard' as deploy user to configure)"

# ── 4. Database backups for both projects ──
echo "[4/6] Setting up backups..."
mkdir -p /opt/nexotalent/backups
cat > /opt/harmoni/backups/backup-all.sh << 'BKEOF'
#!/bin/bash
TS=$(date +%Y%m%d_%H%M%S)
PGPASSWORD="H4rm0n1_Pr0d_2026!" pg_dump -U harmoni -h localhost harmoni_db | gzip > "/opt/harmoni/backups/harmoni_db_${TS}.sql.gz"
PGPASSWORD="N3x0T4l3nt_Pr0d_2026!" pg_dump -U nexotalent -h localhost nexotalent_db | gzip > "/opt/nexotalent/backups/nexotalent_db_${TS}.sql.gz"
find /opt/harmoni/backups -name "*.sql.gz" -mtime +7 -delete
find /opt/nexotalent/backups -name "*.sql.gz" -mtime +7 -delete
echo "$(date) — Backup completed" >> /opt/harmoni/backups/backup.log
BKEOF
chmod +x /opt/harmoni/backups/backup-all.sh
(crontab -l 2>/dev/null | grep -v backup; echo "0 3 * * * /opt/harmoni/backups/backup-all.sh") | crontab -
echo "  Backups configured (daily 3AM, 7-day retention)"

# ── 5. Logrotate for Docker logs ──
echo "[5/6] Setting up logrotate..."
cat > /etc/logrotate.d/docker-containers << 'LREOF'
/var/lib/docker/containers/*/*.log {
    rotate 7
    daily
    compress
    delaycompress
    missingok
    copytruncate
    maxsize 50M
}
LREOF
echo "  Logrotate OK"

# ── 6. Auto-restart on reboot ──
echo "[6/6] Setting up auto-start on reboot..."
cat > /etc/systemd/system/harmoni-docker.service << 'SVCEOF'
[Unit]
Description=Harmoni Docker Compose
Requires=docker.service postgresql.service redis-server.service
After=docker.service postgresql.service redis-server.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/harmoni/app
ExecStart=/usr/bin/docker compose -p harmoni -f docker-compose.prod.yml up -d
ExecStop=/usr/bin/docker compose -p harmoni -f docker-compose.prod.yml down
User=root

[Install]
WantedBy=multi-user.target
SVCEOF

cat > /etc/systemd/system/nexotalent-docker.service << 'SVCEOF'
[Unit]
Description=NexoTalent Docker Compose
Requires=docker.service postgresql.service redis-server.service
After=docker.service postgresql.service redis-server.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/nexotalent/app
ExecStart=/usr/bin/docker compose -p nexotalent -f docker-compose.prod.yml up -d
ExecStop=/usr/bin/docker compose -p nexotalent -f docker-compose.prod.yml down
User=root

[Install]
WantedBy=multi-user.target
SVCEOF

systemctl daemon-reload
systemctl enable harmoni-docker nexotalent-docker
echo "  Auto-start on reboot OK"

# ── Final status ──
echo ""
echo "=== $(date) — All improvements complete ==="
echo ""
docker ps --format "table {{.Names}}\t{{.Status}}"
echo ""
free -h | head -2
echo ""
docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}"
