---
name: server_capacity
description: VPS Contabo capacity analysis and scaling plan for when clients go live
type: project
---

VPS Contabo: 4 cores AMD EPYC, 8GB RAM, 72GB disco (81% usado).
Gunicorn: 3 workers x 2 threads = 6 hilos concurrentes (~30-50 usuarios).
Comparte servidor con NexoTalent y Sophi.

**Why:** Aún no hay clientes en línea. Cuando lleguen, escalar rápido.

**How to apply:**
- Subir workers a 5x4=20 hilos → ~80 usuarios (+400MB RAM, hay espacio)
- Activar Django cache en Redis (DB 0 ya disponible)
- Limpiar disco (queda 15GB, borrar backups/logs viejos)
- Si supera 100 usuarios: considerar separar NexoTalent/Sophi a otro VPS
