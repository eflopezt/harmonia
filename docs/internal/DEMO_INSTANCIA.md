# Instancia Demo — demo.harmoni.pe

**Última revisión:** 2026-04-29

Subdominio aislado con datos ficticios para presentar Harmoni a clientes potenciales sin tocar producción real.

## Arquitectura

| Componente | Producción | Demo |
|---|---|---|
| URL | harmoni.pe | demo.harmoni.pe |
| Puerto interno | 8000 | **8004** |
| BD Postgres | harmoni_db | **harmoni_demo_db** |
| Usuario PG | harmoni | **harmoni_demo** |
| Password PG | H4rm0n1_Pr0d_2026! | **D3m0_2026_Demo!** |
| Redis DB | 0 | **3** (broker) + **4** (results) |
| Contenedor web | harmoni-web | harmoni-demo-web |
| Celery worker | harmoni-celery | harmoni-demo-celery |
| Celery beat | harmoni-beat | harmoni-demo-beat |
| Imagen Docker | harmoni-web-img:latest (compartida) | harmoni-web-img:latest (compartida) |
| Volúmenes | /opt/harmoni/ | /opt/harmoni-demo/ |
| Logs | /opt/harmoni/logs/ | /opt/harmoni-demo/logs/ |

## Acceso

| Dato | Valor |
|---|---|
| URL pública | `https://demo.harmoni.pe` (cuando DNS+SSL estén listos) |
| Usuario | `demo` |
| Password | `demo` |

## Datos cargados (seed inicial)

- 1 empresa: **Demo Empresa SAC** (subdominio="demo")
- 5 áreas, 11 subáreas
- 20 empleados con DNIs ficticios + datos peruanos realistas
- 5 usuarios sistema (rrhh.admin, reclutadora, planillas, bienestar, jefe.ops) con contraseña `Demo2026!`
- 1,330 registros tareo (70 días de asistencia simulada)
- 23 papeletas de vacaciones aprobadas

## Reset diario

Cada día a las **03:00 am** (cron en VPS):
1. Stop containers demo
2. DROP BD + recrear desde schema de producción
3. Restart containers
4. Re-seed completo
5. Resultado: BD limpia con datos prístinos del seed

Script: `/opt/harmoni-demo/reset_demo.sh`
Log: `/opt/harmoni-demo/logs/reset.log`

## Banner "MODO DEMO"

Visible en top de toda página cuando env `DEMO_MODE=True`. Implementado en:
- `personal/context_processors.py:harmoni_context()` — expone `DEMO_MODE` al template
- `templates/base.html` — div fixed top con gradiente naranja-rojo

## Cómo crear el subdominio (pasos pendientes)

### 1. Crear A record en Cloudflare
- Dashboard → harmoni.pe → DNS → Add record
- Type: A, Name: `demo`, IPv4: `212.56.34.166`, Proxy: **off** (gris, no naranja)
- Tiempo: TTL Auto

O vía API con token:
```bash
ZONE_ID=$(curl -s "https://api.cloudflare.com/client/v4/zones?name=harmoni.pe" \
  -H "Authorization: Bearer $TOKEN" | jq -r '.result[0].id')
curl -X POST "https://api.cloudflare.com/client/v4/zones/$ZONE_ID/dns_records" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  --data '{"type":"A","name":"demo","content":"212.56.34.166","ttl":300,"proxied":false}'
```

### 2. Verificar propagación
```bash
dig +short demo.harmoni.pe   # debe responder 212.56.34.166
```

### 3. SSL con Let's Encrypt
```bash
ssh root@212.56.34.166
certbot certonly --webroot -w /var/www/html -d demo.harmoni.pe \
  --agree-tos --email eflopezt@gmail.com --non-interactive
# Actualizar nginx vhost para HTTPS
systemctl reload nginx
```

### 4. Activar Cloudflare proxy (opcional)
Tras SSL funcionando, cambiar el A record a "Proxied" (naranja) si querés CDN/DDoS protection. Asegurate que SSL en Cloudflare esté en modo "Full (strict)".

## Operaciones comunes

### Cambiar contraseña del user demo
```bash
docker exec harmoni-demo-web python manage.py changepassword demo
```

### Cargar más datos sin reset
```bash
docker exec harmoni-demo-web python manage.py seed_demo_presentacion
docker exec harmoni-demo-web python manage.py seed_demo_completar
docker exec harmoni-demo-web python manage.py seed_tareo_inicial
docker exec harmoni-demo-web sh -c "cd /app && PYTHONPATH=/app python /tmp/seed_asis.py"
```

### Logs en vivo
```bash
docker logs -f harmoni-demo-web
```

### Reset manual (sin esperar 03:00 am)
```bash
/opt/harmoni-demo/reset_demo.sh
```

### Dar de baja el demo
```bash
docker stop harmoni-demo-web harmoni-demo-celery harmoni-demo-beat
docker rm harmoni-demo-web harmoni-demo-celery harmoni-demo-beat
sudo -u postgres dropdb harmoni_demo_db
crontab -l | grep -v reset_demo | crontab -
rm -rf /opt/harmoni-demo
rm /etc/nginx/sites-enabled/demo.harmoni.pe
systemctl reload nginx
```

## Notas de seguridad

- Password "demo" es **intencionalmente débil** (cliente no quiere algo memorable). Solo es seguro porque la BD se resetea diariamente.
- Banner aclara explícitamente que es DEMO — el cliente no espera privacidad ni persistencia.
- Sync Synkro **NO está activo** en demo (DEMO_MODE no configura `synkro` DATABASE).
- Datos personales son completamente ficticios.
