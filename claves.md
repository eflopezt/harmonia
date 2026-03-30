# Claves de Acceso - Harmoni ERP

## Produccion (https://harmoni.pe)

### Usuarios de aplicacion

| Usuario | Contrasena | Rol | Descripcion |
|---------|-----------|-----|-------------|
| `admin` | `Harmoni2026!` | Superadmin | Acceso total a todos los modulos |
| `gerente` | `Gerente2026!` | Staff/Gerente | Acceso a dashboards y reportes de su area |
| `ediaz` | (por definir) | Staff | Usuario de negocio |

### VPS (DigitalOcean)

| Servicio | Host | Usuario | Autenticacion |
|----------|------|---------|---------------|
| SSH | `212.56.34.166:22` | `root` | Llave SSH `~/.ssh/id_ed25519` |
| Web (nginx) | `harmoni.pe:443` | - | SSL Let's Encrypt |
| Django (interno) | `localhost:8000` | - | Gunicorn 3 workers |

### Base de datos (PostgreSQL)

| Campo | Valor |
|-------|-------|
| Host | `localhost:5432` |
| Base de datos | `harmoni_db` |
| Usuario | `harmoni` |
| Contrasena | `H4rm0n1_Pr0d_2026!` |

### Redis

| Campo | Valor |
|-------|-------|
| Host | `localhost:6379` |
| Contrasena | `H4rm0n1_R3d1s_2026!` |
| DB 0 | Broker Celery |
| DB 1 | Result Backend Celery |

### Django

| Variable | Valor |
|----------|-------|
| `DJANGO_SECRET_KEY` | `cVKMNM0lCZMSy8DrZiV56OSGROY_VqhS2b6TKwoj8_dQpXL0W90bp44ar1VU_LULkKg` |
| `DJANGO_SETTINGS_MODULE` | `config.settings.production` |

### GitHub

| Campo | Valor |
|-------|-------|
| Repo | `https://github.com/eflopezt/harmoni.git` |
| Branch | `main` |

## Docker Containers (produccion)

| Container | Imagen | Network | Funcion |
|-----------|--------|---------|---------|
| `harmoni-web` | `harmoni-web-img` | host | Django + Gunicorn |
| `harmoni-celery` | `harmoni-celery` | host | Worker de tareas async |
| `harmoni-beat` | `harmoni-beat` | host | Scheduler de tareas periodicas |

## Comando de Deploy

```bash
ssh -i ~/.ssh/id_ed25519 root@212.56.34.166 "
cd /opt/harmoni/app && git pull &&
docker stop harmoni-web && docker rm harmoni-web &&
docker run -d --name harmoni-web --network host --restart unless-stopped \
  -v /opt/harmoni/app:/app -v /opt/harmoni/staticfiles:/app/staticfiles \
  -e DJANGO_SETTINGS_MODULE=config.settings.production \
  -e DATABASE_URL=postgresql://harmoni:H4rm0n1_Pr0d_2026\!@localhost:5432/harmoni_db \
  -e REDIS_URL=redis://:H4rm0n1_R3d1s_2026\!@localhost:6379/0 \
  -e CELERY_BROKER_URL=redis://:H4rm0n1_R3d1s_2026\!@localhost:6379/0 \
  -e CELERY_RESULT_BACKEND=redis://:H4rm0n1_R3d1s_2026\!@localhost:6379/1 \
  -e DJANGO_SECRET_KEY=cVKMNM0lCZMSy8DrZiV56OSGROY_VqhS2b6TKwoj8_dQpXL0W90bp44ar1VU_LULkKg \
  -e DJANGO_ALLOWED_HOSTS=localhost,harmoni.pe,www.harmoni.pe,212.56.34.166 \
  -e DJANGO_DEBUG=False -e SECURE_SSL_REDIRECT=False \
  harmoni-web-img gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 3 --timeout 120
"
```

## Notas

- El dominio `harmoni.pe` pasa por Cloudflare (solo HTTP/HTTPS). SSH debe ir directo a la IP `212.56.34.166`.
- PostgreSQL y Redis corren como servicios nativos del host (no en Docker).
- Los containers usan `--network host` para conectar a los servicios locales.
- SSL es terminado por nginx con certificados Let's Encrypt.
