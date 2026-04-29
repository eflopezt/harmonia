---
name: Demo Harmoni — demo.harmoni.pe
description: Subdominio demo aislado con datos ficticios para presentar a clientes potenciales
type: project
originSessionId: 14421100-76fd-4e94-bb4c-a0c61db61e98
---
## Estado al 2026-04-29

### ✅ Listo en VPS Contabo
- **BD**: `harmoni_demo_db` (PostgreSQL) con schema clonado de producción + extensión vector
- **Usuario PG**: `harmoni_demo` / `D3m0_2026_Demo!`
- **Redis DB**: 3 (broker) y 4 (results) — separadas de producción
- **Contenedores**: `harmoni-demo-web` (puerto **8004**), `harmoni-demo-celery`, `harmoni-demo-beat`
- **SECRET_KEY**: guardado en `/opt/harmoni-demo/.env.demo` (chmod 600)
- **Volúmenes**: `/opt/harmoni-demo/{staticfiles,media,logs}`
- **Empresa**: `Demo Empresa SAC` con `subdominio='demo'`, RUC ficticio 20999999999
- **Superuser**: `demo` / `demo`
- **Datos**: 20 empleados, 5 áreas, 11 subáreas, 1,330 registros tareo (70 días), 23 papeletas
- **Banner MODO DEMO**: implementado vía env `DEMO_MODE=True` + context processor + base.html
- **Nginx vhost**: `/etc/nginx/sites-available/demo.harmoni.pe` (HTTP, esperando SSL)
- **Reset diario**: cron `0 3 * * * /opt/harmoni-demo/reset_demo.sh` — drop+restore schema+seed completo
- **Internamente accesible**: `curl -H "Host: demo.harmoni.pe" http://localhost/admin/login/` → 200 OK

### ⏳ Pendiente
1. **DNS A record**: `demo.harmoni.pe → 212.56.34.166` (esperando API token Cloudflare del usuario)
2. **SSL Let's Encrypt**: certbot certonly --nginx después de propagación DNS
3. **Smoke test final**: login + recorrido de módulos (asistencia, papeletas, planilla, reclutamiento)

### Para retomar
Cuando el user vuelva, pedirle el API token Cloudflare:
1. Login dash.cloudflare.com → Profile → API Tokens → Create Token
2. Template "Edit zone DNS" → Specific zone harmoni.pe → Create
3. Copiar token

Con el token:
```bash
TOKEN=...
curl -X POST "https://api.cloudflare.com/client/v4/zones/$ZONE_ID/dns_records" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  --data '{"type":"A","name":"demo","content":"212.56.34.166","ttl":300,"proxied":false}'
```

(Conviene desactivar proxy de Cloudflare para que Let's Encrypt pueda validar.)

Después:
```bash
ssh root@212.56.34.166 'certbot certonly --webroot -w /var/www/html -d demo.harmoni.pe \
  --agree-tos --email eflopezt@gmail.com --non-interactive'
# Actualizar nginx vhost para listen 443 ssl + proxy_pass
systemctl reload nginx
```

### Aislamiento de producción
- Misma imagen Docker `harmoni-web-img:latest` (compartida con producción)
- Volumen `/opt/harmoni/app:/app:ro` (solo lectura — no afecta prod si el demo intenta escribir)
- BD/Redis/contenedores totalmente separados
- El sync Synkro NO está activado en demo (DEMO_MODE no agrega `synkro` a DATABASES)

### Decisión pendiente
El user pidió 6 empleados pero el seed creó 20 (más realista). Confirmar al volver:
- (a) Mantener 20 → no hacer nada
- (b) Reducir a 6 → modificar `seed_demo_presentacion` para crear solo 6 + correr reset

### Credenciales demo
- URL final: `https://demo.harmoni.pe` (después del DNS+SSL)
- Usuario: `demo`
- Password: `demo`
- Banner avisa que es modo DEMO con reset nocturno
