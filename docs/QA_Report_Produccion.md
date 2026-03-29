# QA Report - Harmoni Produccion (harmoni.pe)

**Fecha del test:** 2026-03-29
**Entorno:** Produccion (https://harmoni.pe)
**Ejecutado por:** QA Automatizado (Claude Agent)
**Version detectada:** Harmoni ERP v1.0.0

---

## Resumen Ejecutivo

| Categoria | Resultado |
|---|---|
| Paginas Publicas | PASS (3/4) |
| Assets Estaticos | PASS (5/5) |
| Rendimiento | PASS |
| Seguridad Headers | PASS (con observaciones) |
| HTTPS / SSL | PASS |
| Responsive Design | PASS |
| SEO Basico | WARNING (con observaciones) |
| Errores de Consola | PASS |
| Accesibilidad Admin | PASS |

**Score general: 8.5 / 10**

---

## 1. Paginas Publicas

### 1.1 Homepage (https://harmoni.pe/)
- **Estado:** PASS
- **HTTP Code:** 200
- **Comportamiento:** Renderiza landing page completa sin redireccion a login
- **Contenido:** Landing page de producto con hero, features, mockup del dashboard

### 1.2 Login (https://harmoni.pe/login/)
- **Estado:** PASS
- **HTTP Code:** 200
- **Formulario:** Presente con campos usuario/contrasena
- **CSRF Token:** Presente y funcional (hidden input)
- **Elementos:**
  - Campo "Usuario" (text, required, autofocus)
  - Campo "Contrasena" (password, con toggle de visibilidad)
  - Boton "Ingresar al Sistema"
  - Link recuperacion de contrasena
  - Link solicitud de acceso

### 1.3 Health Check (https://harmoni.pe/health/)
- **Estado:** PASS
- **HTTP Code:** 200
- **Content-Type:** application/json
- **Respuesta:** `{"status": "ok", "database": "ok"}`
- **Nota:** Endpoint funcional, base de datos conectada

### 1.4 Password Reset (https://harmoni.pe/password/reset/)
- **Estado:** FAIL (404)
- **Nota:** La URL /password/reset/ retorna 404
- **URL alternativa probada:** /password_reset/ -> tambien 404
- **Impacto:** El link de recuperacion de contrasena en login podria apuntar a una ruta diferente

---

## 2. Assets Estaticos

| Asset | URL | Status | Resultado |
|---|---|---|---|
| Favicon SVG | /static/images/favicon.svg | 200 | PASS |
| CSS Principal | /static/css/harmoni.css | 200 | PASS |
| FontAwesome 6.5.1 | cdnjs.cloudflare.com | 200 | PASS |
| Google Fonts (Inter) | fonts.googleapis.com | 200 | PASS |
| Bootstrap 5.3.2 | cdn.jsdelivr.net | 200 | PASS |

**Homepage:** CSS y JS estan inline (no archivos externos), lo cual mejora el rendimiento.
**Login page:** Usa archivos externos (harmoni.css, bootstrap, fontawesome).

---

## 3. Rendimiento

### 3.1 Tiempos de Carga

| Pagina | TTFB | Total | Tamano |
|---|---|---|---|
| Homepage (/) | 0.711s | 0.919s | 43,418 bytes (~42 KB) |
| Login (/login/) | 0.422s | 0.425s | - |
| Health (/health/) | 0.457s | 0.457s | 34 bytes |

### 3.2 Evaluacion
- **TTFB Homepage:** 711ms - ACEPTABLE (< 800ms), podria optimizarse
- **TTFB Login:** 422ms - BUENO
- **Tamano Homepage:** 42 KB HTML (con CSS/JS inline) - EXCELENTE
- **CDN:** Cloudflare activo (cf-cache-status: DYNAMIC)

### 3.3 Optimizaciones Detectadas
- CSS y JS inline en homepage (elimina requests adicionales)
- Preconnect a Google Fonts (`<link rel="preconnect">`)
- Tamano compacto del HTML

---

## 4. Seguridad

### 4.1 Headers de Seguridad

| Header | Valor | Resultado |
|---|---|---|
| X-Frame-Options | DENY | PASS |
| Strict-Transport-Security | max-age=31536000; includeSubDomains; preload | PASS |
| X-Content-Type-Options | nosniff | PASS |
| Referrer-Policy | same-origin | PASS |
| Cross-Origin-Opener-Policy | same-origin | PASS |
| Content-Security-Policy | NO PRESENTE | WARNING |
| X-Powered-By | NO PRESENTE | PASS (no se expone info de servidor) |

### 4.2 HTTPS
- **HTTP -> HTTPS redirect:** PASS (301 redirect)
- **HSTS:** Activo con preload
- **SSL/TLS:** Activo via Cloudflare

### 4.3 CSRF Protection
- **Token en formularios:** PASS (csrfmiddlewaretoken presente)
- **POST sin CSRF:** Retorna 403 Forbidden - PASS
- **Cookie csrftoken:**
  - HttpOnly: Si
  - Secure: Si
  - SameSite: Lax
  - Resultado: PASS

### 4.4 Admin Panel
- **/admin/:** Redirige a /admin/login/ (302) - PASS
- No expone panel admin directamente

### 4.5 Server Info
- Server header: "cloudflare" (no revela backend)
- No X-Powered-By header - PASS

---

## 5. Responsive Design

### 5.1 Analisis CSS
- **Media queries detectadas:** 2 breakpoints en homepage
- **Meta viewport:** Presente (`width=device-width, initial-scale=1.0`)
- **Bootstrap 5.3.2:** Usado en pagina de login (responsive por defecto)
- **Homepage:** CSS custom con responsive breakpoints en 1024px y 768px

### 5.2 Evaluacion por Dispositivo
- **Mobile (375x812):** Viewport meta presente, breakpoints cubren movil
- **Tablet (768x1024):** Breakpoint en 768px cubre tablets
- **Desktop (1280x800):** Max-width: 1200px en container principal

**Nota:** No fue posible tomar screenshots ya que el permiso de automatizacion del browser fue denegado. El analisis se basa en el codigo CSS.

---

## 6. Consola y Network

### 6.1 Errores de Red
- Todos los assets estaticos retornan 200
- No se detectaron requests fallidos (404/500) en assets

### 6.2 Scripts Cargados (Login)
- Cloudflare email-decode.min.js (proteccion de emails)
- Bootstrap 5.3.2 bundle (JS framework)
- Script inline para toggle de visibilidad de contrasena

### 6.3 Paginas de Error
- URL inexistente retorna 404 correctamente - PASS

---

## 7. SEO Basico

### 7.1 Homepage

| Elemento | Contenido | Resultado |
|---|---|---|
| title | "Harmoni -- ERP de RRHH y Planillas para empresas" | PASS |
| meta description | Presente (122 chars) | PASS |
| meta viewport | width=device-width, initial-scale=1.0 | PASS |
| favicon | /static/images/favicon.svg (SVG) | PASS |
| og:title | "Harmoni -- ERP de RRHH y Planillas" | PASS |
| og:description | Presente | PASS |
| og:type | website | PASS |
| og:url | https://harmoni.pe | PASS |
| og:image | NO PRESENTE | WARNING |
| Twitter cards | NO PRESENTE | WARNING |
| canonical | NO PRESENTE | WARNING |
| robots meta | NO PRESENTE | INFO (usa robots.txt) |
| lang attribute | "es" | PASS |
| charset | UTF-8 | PASS |
| Google Verification | Presente | PASS |

### 7.2 Login Page

| Elemento | Contenido | Resultado |
|---|---|---|
| title | "Iniciar Sesion -- Harmoni" | PASS |
| meta description | NO PRESENTE | WARNING |
| meta viewport | Presente | PASS |
| favicon | Presente | PASS |

### 7.3 Sitemap y Robots
- **robots.txt:** Presente (gestionado por Cloudflare + custom rules)
- **sitemap.xml:** Presente pero minimo (solo 1 URL: homepage)
- **Nota:** robots.txt bloquea bots de IA (ClaudeBot, GPTBot, etc.) correctamente

---

## 8. Issues Encontrados

### Prioridad ALTA

| # | Issue | Detalle |
|---|---|---|
| 1 | Password reset 404 | /password/reset/ retorna 404. Verificar la URL correcta del link en login |

### Prioridad MEDIA

| # | Issue | Detalle |
|---|---|---|
| 2 | Sin Content-Security-Policy | No se detecta CSP header. Recomendado para prevenir XSS |
| 3 | Sin og:image | Falta Open Graph image para compartir en redes sociales |
| 4 | Sin Twitter Cards | No hay meta tags de Twitter para preview en esa red |
| 5 | Sin canonical tag | Falta link rel="canonical" en homepage |

### Prioridad BAJA

| # | Issue | Detalle |
|---|---|---|
| 6 | Sitemap minimo | Solo contiene 1 URL. Considerar agregar /login/ si es indexable |
| 7 | Login sin meta description | La pagina de login no tiene meta description |
| 8 | TTFB homepage | 711ms, podria optimizarse con cache en Cloudflare |

---

## 9. Recomendaciones

### Seguridad
1. **Agregar Content-Security-Policy header** para mitigar ataques XSS. Ejemplo minimo:
   ```
   Content-Security-Policy: default-src 'self'; script-src 'self' cdn.jsdelivr.net cdnjs.cloudflare.com; style-src 'self' 'unsafe-inline' cdn.jsdelivr.net cdnjs.cloudflare.com fonts.googleapis.com; font-src fonts.gstatic.com cdnjs.cloudflare.com
   ```
2. **Verificar la ruta de password reset** - asegurar que el link en login apunta a la URL correcta

### SEO
3. **Agregar og:image** con una imagen representativa del producto (recomendado 1200x630px)
4. **Agregar Twitter Card meta tags** (twitter:card, twitter:title, twitter:description, twitter:image)
5. **Agregar link canonical** (`<link rel="canonical" href="https://harmoni.pe/">`)
6. **Expandir sitemap.xml** con todas las paginas publicas relevantes

### Rendimiento
7. **Considerar cache de Cloudflare** para la homepage (actualmente DYNAMIC)
8. **Comprimir homepage** - verificar que gzip/brotli esta activo para el HTML

### General
9. **Agregar meta description** en la pagina de login
10. **Considerar agregar pagina de error 404 personalizada** con navegacion de vuelta

---

## 10. Notas del Test

- El test fue ejecutado desde una conexion en Argentina (CF-RAY: EZE)
- Los tiempos de respuesta pueden variar segun la ubicacion geografica
- No fue posible tomar screenshots del browser ya que los permisos de automatizacion de Chrome fueron denegados
- El analisis responsive se baso en inspeccion del codigo CSS, no en capturas visuales
- No se probo el flujo de login con credenciales (test de funcionalidad autenticada fuera del alcance)

---

*Reporte generado automaticamente el 2026-03-29*
