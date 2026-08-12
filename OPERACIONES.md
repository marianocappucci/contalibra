# Contalibra — Guía de Operaciones

Guía de referencia para gestionar el servidor, dar de alta clientes nuevos y
desplegar actualizaciones del sistema.

---

## Índice

1. [Arquitectura](#arquitectura)
2. [Entornos dev y producción](#entornos-dev-y-producción)
3. [Setup inicial del servidor](#setup-inicial-del-servidor)
4. [Alta de un cliente nuevo](#alta-de-un-cliente-nuevo)
5. [Gestión diaria con panel_admin.py](#gestión-diaria-con-panel_adminpy)
6. [Migrar la base antes de desplegar](#migrar-la-base-antes-de-desplegar)
7. [Desplegar una actualización](#desplegar-una-actualización)
8. [Cuándo reconstruir la imagen vs solo reiniciar](#cuándo-reconstruir-la-imagen-vs-solo-reiniciar)
9. [Backup y restauración](#backup-y-restauración)
10. [Proxy y SSL (Nginx Proxy Manager)](#proxy-y-ssl-nginx-proxy-manager)
11. [Gestión del estado del servicio](#gestión-del-estado-del-servicio)
12. [Website de marketing (contalibra.com.ar)](#website-de-marketing-contalibracomar)
13. [Estructura de directorios](#estructura-de-directorios)

---

## Entornos dev y producción

El servidor corre **una instancia de dev** y **N instancias multi-tenant**, una por
cliente. No hay un "entorno de producción" único: cada cliente es una instancia
aislada bajo `clientes/<slug>/`, con su contenedor, su sidecar de datos y su pin de
imagen propios.

| | Desarrollo | Cada instancia de cliente |
|---|---|---|
| Puerto | `8071` | uno por instancia, desde `8070` |
| Contenedor Docker | `contalibra-dev` | `contalibra` (compulibra), `contalibra-demo`, … |
| docker-compose | `docker-compose.yml` (raíz del repo) | `clientes/<slug>/docker-compose.yml` |
| Base de datos | PostgreSQL, sidecar `contalibra-postgres` | PostgreSQL, un sidecar propio por instancia |
| Código | Volumen montado `./:/app` (hot-reload) | Copiado en una imagen **pineada** |
| Badge en UI | `DEV` amarillo en sidebar | Sin badge |

> El checkout del VPS (`/root/contalibra`) corre **`main`**, y de él salen tanto el
> bind mount de dev como los builds de las instancias de cliente.

> ⚠️ **`clientes/` está en el `.gitignore`**: los compose de instancia viven sólo en
> el VPS. Son configuración de instancia, no código, y no llegan por `git pull`.

> ⚠️ **El contenedor de la instancia `compulibra` se llama `contalibra`, a secas** —
> nombre histórico, anterior a la convención `<producto>-<slug>`. Importa al pasarle
> instancias a cualquier comando que reciba nombres de contenedor.

### Flujo de trabajo diario

Todo el trabajo se hace en la rama `develop`. Los cambios se pushean libremente.

```bash
git checkout develop       # siempre trabajar en develop
# ... editar código ...
git add -A
git commit -m "descripcion"
git push origin develop
```

### Arrancar entorno de desarrollo

```bash
cd /root/contalibra
docker compose up -d --build    # usa docker-compose.yml → puerto 8071
```

### Promover cambios a producción

> 🔴 **`scripts/deploy-prod.sh` ya no existe.** Se eliminó en el commit `ccb3137`
> junto con `docker-compose.prod.yml`, cuando `compulibra` —la instancia de
> producción original— pasó a vivir en `clientes/compulibra/` como cualquier otro
> cliente. Aquel script desplegaba **un solo tenant**: construía una imagen y
> reiniciaba el contenedor `contalibra` y nada más. Hoy hay N instancias, cada una
> con su pin de imagen, y el deploy las mueve a todas.

La promoción tiene dos mitades: **el código va por PR**, y **el deploy se hace en el
servidor**.

**1. Promover el código a `main`** (desde WSL local, no en el servidor):

```bash
gh pr create --base main --head develop --title "Deploy: <resumen>"
# con el CI en verde:
gh pr merge --merge
```

**2. Desplegar en el servidor**, desde `/root/contalibra` (que corre `main`):

```bash
cd /root/contalibra
git pull

# ⚠️ Antes de levantar nada: ver "Migrar la base antes de desplegar"
# Sin ese paso el código nuevo puede escribir columnas que la base no tiene.

./.venv-scripts/bin/python3 scripts/panel_admin.py actualizar
```

`actualizar` construye **una imagen nueva** con tag de deploy
(`contalibra:vAAAA.MM.DD-hhmm`), repinea el `image:` del compose de cada instancia
**que esté corriendo** y la levanta con `docker compose up -d`. Una instancia detenida
se saltea **sin repinear**: queda en la versión que ya tenía, para que arrancarla más
tarde no la salte a código que no se desplegó para ella.

Con un slug despliega una sola instancia; sin argumentos, todas:

```bash
./.venv-scripts/bin/python3 scripts/panel_admin.py actualizar compulibra
```

> **Los scripts corren con `./.venv-scripts/bin/python3`, no con el `python3` del
> sistema.** `nuevo_cliente.py` y `panel_admin.py` son wrappers finos sobre
> `libracore.provisioning`, y el Python del sistema del VPS no tiene `pip` por
> política de Debian (PEP 668). Ese venv está **gitignored**: no llega por `git pull`.
> Si LibraCore subió de versión, hay que actualizarlo también — `actualizar` avisa
> cuando el venv quedó atrás del pin del `pyproject.toml`.

### Verificar qué quedó desplegado

```bash
./.venv-scripts/bin/python3 scripts/panel_admin.py versiones
```

Muestra dos columnas distintas a propósito: **pineado** (lo que dice el compose, la
intención) y **corriendo** (lo que dice `docker inspect`, el hecho). Un contenedor
creado desde `:latest` sigue diciendo `:latest` aunque el tag ya apunte a otra imagen,
así que comparar nombres da un falso "todo en orden".

### Versionado

> **`version.py` ya no existe en este repo.** Se fue con el deploy de un solo tenant.

La versión de un deploy es un **timestamp**, `vAAAA.MM.DD-hhmm`, y lo que nombra es
**la imagen** — que es lo que permite que el compose de cada instancia pinee una
versión concreta en vez de un `:latest` mutable. Es a propósito que no sea la versión
del producto: un deploy puede repetir código (un rebuild por un bump de dependencia,
por ejemplo), y lo que hay que poder distinguir es el deploy, no el código.

Los cambios de cara al usuario siguen yendo a `CHANGELOG.md`.

---

## Arquitectura

```
VPS
├── /root/contalibra/          ← código fuente del sistema (este repo)
│   ├── web/                   ← aplicación FastAPI
│   ├── scripts/               ← herramientas de administración
│   └── clientes/              ← un subdirectorio por cliente
│       ├── mitienda/
│       │   ├── docker-compose.yml
│       │   ├── cliente.json   ← metadatos del cliente y versión desplegada
│       │   ├── backups/       ← backups de la instancia
│       │   └── data/          ← montado en /app/data dentro del contenedor
│       │       ├── config.json
│       │       ├── logos/
│       │       └── arca_certs/
│       └── otrocomercio/
│           └── ...
└── nginx-proxy-manager        ← proxy inverso con SSL automático
```

**Principio clave**: cada instancia de cliente es un silo. Tiene su propio
contenedor, su propio **sidecar de PostgreSQL** (sin puerto publicado, en una red
`contalibra-<slug>-datos` propia), su propio `data/` con la configuración y los
adjuntos, y su propio pin de imagen. No hay ningún componente de datos compartido
entre instancias.

El código **va copiado dentro de la imagen**, que cada compose pinea por tag. Por eso
un cambio de código no se aplica reiniciando: hay que construir una imagen nueva y
mover la instancia a ella, que es lo que hace `panel_admin.py actualizar`. La única
excepción es la instancia de **dev**, que monta `./:/app` y corre con `--reload`.

---

## Setup inicial del servidor

Solo se hace una vez cuando se instala el sistema en un VPS nuevo.

### 1. Clonar el repositorio

```bash
cd /root
git clone <url-del-repo> contalibra
cd contalibra
```

### 2. Construir la imagen Docker

```bash
docker build -t contalibra:latest .
```

Esto tarda 2-3 minutos la primera vez (descarga Python 3.12-slim e instala
dependencias). Las siguientes veces es mucho más rápido por caché.

### 3. Configurar Nginx Proxy Manager (opcional pero recomendado)

Si vas a usar dominios con SSL automático:

```bash
./.venv-scripts/bin/python3 scripts/npm_setup.py
```

El script pregunta la URL de NPM (típicamente `http://localhost:81`), las
credenciales de su panel admin, y el `forward_host` (normalmente `172.17.0.1`
que es el gateway Docker). Guarda la config en `scripts/.npm_config.json`
(excluido del repo).

---

## Alta de un cliente nuevo

```bash
cd /root/contalibra
./.venv-scripts/bin/python3 scripts/nuevo_cliente.py
```

El script es interactivo y guía paso a paso:

```
============================================================
  CONTALIBRA — Alta de nuevo cliente
============================================================
Nombre del comercio / empresa: La Panadería del Centro
Identificador (slug) [la-panaderia-del-centro]:        ← Enter para aceptar
Dominio (ej: mitienda.com, Enter para omitir): panaderia.midominio.com
Puerto HTTP [8071]:                                    ← autodetecta el siguiente libre
Usuario admin [admin]:
Contraseña admin (Enter = generar):                    ← deja vacío para generar una segura
Nombre completo del admin [La Panadería del Centro]:
```

Luego muestra un resumen y pide confirmación:

```
------------------------------------------------------------
  Comercio:    La Panadería del Centro
  Slug:        la-panaderia-del-centro
  Contenedor:  contalibra-la-panaderia-del-centro
  Puerto:      8071
  Dominio:     panaderia.midominio.com
  Admin:       admin / xK9mP2nQrT4w
------------------------------------------------------------
¿Confirmar? [S/n]:
```

Al confirmar:
1. Crea `clientes/la-panaderia-del-centro/` con toda la estructura de directorios
2. Genera `docker-compose.yml` con el puerto asignado y las credenciales
3. Crea `data/config.json` inicial
4. Levanta el contenedor (`docker compose up -d`)
5. Si NPM está configurado, ofrece crear el proxy con SSL automáticamente

**Al finalizar muestra las credenciales — guardalas, no se vuelven a mostrar.**

### Acceso inmediato

```
URL local:  http://localhost:8071
Dominio:    https://panaderia.midominio.com   (si configuraste el proxy)
```

El cliente ya puede entrar y completar los datos de su empresa en
`/config` → pestaña "Empresa".

### Habilitar módulos

Los módulos se asignan según el plan del cliente desde el backoffice
(https://admin.contalibra.com.ar), sección Plan de cada cliente. Ya no existe
una pantalla de auto-gestión de módulos dentro del sistema del cliente.

```bash
./.venv-scripts/bin/python3 scripts/panel_admin.py
# → opción 2 (info) para ver el slug exacto
```

---

## Gestión diaria con panel_admin.py

```bash
cd /root/contalibra
./.venv-scripts/bin/python3 scripts/panel_admin.py           # menú interactivo
./.venv-scripts/bin/python3 scripts/panel_admin.py listar    # lista rápida desde CLI
```

### Menú disponible

| Opción | Comando CLI | Descripción |
|--------|-------------|-------------|
| `1` | `listar` | Lista todos los clientes con estado del contenedor |
| `2` | `info <slug>` | Detalle de un cliente: URL, puerto, credenciales |
| `3` | `start <slug>` | Inicia el contenedor |
| `4` | `stop <slug>` | Detiene el contenedor |
| `5` | `restart <slug>` | Reinicia el contenedor |
| `6` | `logs <slug>` | Muestra logs en tiempo real (Ctrl+C para salir) |
| `7` | `backup <slug>` | Backup completo (tar.gz) + copia de la DB |
| `rb` | `restore-db <slug>` | Restaura la DB desde un backup |
| `lb` | `list-backups <slug>` | Lista backups de DB disponibles |
| `sa` | `activar <slug>` | Activa el servicio (acceso normal) |
| `sp` | `pausar <slug>` | Pausa (muestra banner de aviso, sin cortar acceso) |
| `ss` | `suspender <slug>` | Suspende (bloquea el acceso completamente) |
| `se` | `estado <slug>` | Muestra el estado actual del servicio |

---

## Migrar la base antes de desplegar

**Paso obligatorio de todo deploy que traiga una versión nueva de LibraCore.**

Las tablas del motor —`clients`, facturación, caja, recibos— las define **LibraCore**,
no este repo, y su schema evoluciona con una cadena de migraciones de Alembic. Cuando
sube el pin de `libracore` en `pyproject.toml`, el código nuevo puede esperar columnas
que la base todavía no tiene.

> 🔴 **Sin este paso, el código nuevo escribe contra un schema viejo.** Y no falla al
> arrancar, que es lo que lo hace peligroso: falla más tarde, cuando alguien toca la
> pantalla que usa la columna nueva — y para entonces la instancia ya está sirviendo.

### Setup único: el script no llega por `git pull`

`migrar_instancias.sh` vive en el repo de **LibraCore**, en `scripts/` — **fuera del
paquete Python**, así que no lo trae `pip install libracore` ni el `git pull` de este
repo. Hace falta un checkout del motor en el servidor:

```bash
git clone git@github-libracore:marianocappucci/libracore.git /root/libracore
```

El alias `github-libracore` ya está en el `~/.ssh/config` del VPS, apuntando a la
deploy key de solo lectura de ese repo.

### Correr las migraciones

En el servidor, **después del `git pull` de este repo y antes de `actualizar`**:

```bash
git -C /root/libracore pull

# 1. DRY-RUN (es el default): dice qué instancias encontró y contra qué base iría
LIBRACORE_REF=v1.28.4 /root/libracore/scripts/migrar_instancias.sh \
  contalibra-dev contalibra-demo contalibra

# 2. Revisada la lista, aplicar:
LIBRACORE_REF=v1.28.4 /root/libracore/scripts/migrar_instancias.sh --si \
  contalibra-dev contalibra-demo contalibra
```

El dry-run imprime, sin tocar nada:

```
LibraCore ref: v1.28.4
MODO DRY-RUN — nada se va a modificar (pasá --si para aplicar)

→ contalibra-dev
    base: postgresql://***:***@contalibra-postgres:5432/contalibra
    red:  contalibra-dev-datos
```

**`LIBRACORE_REF` es el tag que pinea el `pyproject.toml` de _este_ repo**, no un
número común a la familia: cada producto pinea su propia versión del motor.

```bash
grep libracore pyproject.toml
```

**Los argumentos son nombres de contenedor, no slugs** — y el de `compulibra` es
`contalibra` a secas.

> **El dry-run no es una formalidad.** La lista sale de inspeccionar contenedores, así
> que una instancia de cliente pasada por error se migra igual que una de dev. Mirar
> la lista antes de `--si`.

Antes de aplicar sobre una instancia de cliente, backup:

```bash
./.venv-scripts/bin/python3 scripts/panel_admin.py backup compulibra
```

### Por qué un contenedor efímero y no `alembic` en el host

> 🔴 **El host no puede resolver la URL de una instancia.** El destino es
> `postgresql://…@contalibra-postgres:5432/…`, y ese nombre es un **alias de la red de
> Docker** del sidecar de datos: desde afuera de esa red no existe. Correr las
> migraciones derecho en el host falla con *"could not translate host name"*.

Por eso el script las corre en un contenedor efímero adosado a la **misma red** que la
instancia. Las URLs se imprimen siempre enmascaradas: la de PostgreSQL lleva la
contraseña del sidecar adentro.

---

## Desplegar una actualización

### Flujo normal

Cada instancia corre una **imagen pineada** con el código copiado adentro, así que un
deploy es siempre: traer el código, migrar la base, y construir y mover las instancias
a la imagen nueva.

```bash
cd /root/contalibra

# 1. Traer los cambios del repo
git pull

# 2. Migrar la base — ver "Migrar la base antes de desplegar"
LIBRACORE_REF=$(grep -oP 'libracore\.git@\K[^"]+' pyproject.toml) \
  /root/libracore/scripts/migrar_instancias.sh --si \
  contalibra-dev contalibra-demo contalibra

# 3. Construir la imagen nueva y mover las instancias a ella
./.venv-scripts/bin/python3 scripts/panel_admin.py actualizar
```

El paso 3 hace el build: **no hay un `docker build` aparte**, tampoco cuando cambian
las dependencias de `pyproject.toml`. `actualizar` construye la imagen con tag de
deploy y recién entonces repinea y levanta cada instancia.

> ⚠️ **El orden importa.** `actualizar` levanta los contenedores con el código nuevo
> apenas termina el build. Si las migraciones no corrieron antes, el código nuevo
> queda sirviendo contra el schema viejo.

> **La instancia de dev es la excepción**: monta `./:/app` y corre uvicorn con
> `--reload`, así que toma el código nuevo con el `git pull`, sin build. Su base **sí**
> necesita las migraciones igual.

### Actualizar un solo cliente (sin afectar a los demás)

```bash
./.venv-scripts/bin/python3 scripts/panel_admin.py actualizar compulibra
```

`restart` sólo reinicia el contenedor con la imagen que ya tenía pineada — **no trae
código nuevo**:

```bash
./.venv-scripts/bin/python3 scripts/panel_admin.py restart compulibra
```

### Verificar que todo quedó bien

```bash
# Estado de todas las instancias
./.venv-scripts/bin/python3 scripts/panel_admin.py listar

# Qué versión quedó pineada y cuál está corriendo de verdad
./.venv-scripts/bin/python3 scripts/panel_admin.py versiones

# Logs de una instancia, si hay problemas
./.venv-scripts/bin/python3 scripts/panel_admin.py logs compulibra
```

---

## Cuándo reconstruir la imagen vs solo reiniciar

En las instancias de cliente el código viaja **dentro de la imagen**, así que casi todo
cambio del repo necesita `actualizar` (que construye y mueve). `restart` sirve para
cambios que no son código.

| Cambio realizado | Qué correr |
|------------------|------------|
| Código Python (`.py`) | `actualizar` |
| Templates HTML / CSS / JS | `actualizar` |
| `pyproject.toml` (nuevas dependencias) | `actualizar` |
| `Dockerfile` | `actualizar` |
| Pin de `libracore` en `pyproject.toml` | **migrar** y después `actualizar` |
| Variables de entorno en el compose de la instancia | `restart` |
| Estado del servicio (activar/pausar/suspender) | nada — es inmediato |

---

## Backup y restauración

> ⚠️ **Esta sección describe el mecanismo de la época de SQLite y quedó atrás del corte
> a PostgreSQL.** Sigue siendo cierta para los adjuntos y la configuración de `data/`,
> pero **no para la base**:
>
> - `restore-db` y `list-backups` operan sobre archivos `.db` de SQLite. En una
>   instancia ya migrada, el `.db` que queda en `data/` está **congelado en el momento
>   del corte** — restaurarlo no revierte la base que la instancia usa de verdad, y no
>   avisa.
> - El respaldo real de PostgreSQL lo hace un `pg_dump` por instancia, desde el cron
>   nocturno del VPS (`dump_postgres_instancias.sh`, 03:40). Deja los `.dump` en
>   `clientes/<slug>/backups/`, al lado de los `.db` viejos.
>
> Documentar el backup/restore de PostgreSQL para este producto está **pendiente**.
> Hasta entonces, ante una restauración de base, mirar el dump, no el `.db`.

### Backup manual desde el panel admin

```bash
./.venv-scripts/bin/python3 scripts/panel_admin.py backup mitienda
```

Genera dos archivos:
- `clientes/mitienda_backup_YYYYMMDD_HHMMSS.tar.gz` — todo el directorio `data/`
- `clientes/mitienda/backups/contalibra_YYYYMMDD_HHMMSS.db` — solo la DB

### Restaurar la DB de un cliente

```bash
# Interactivo (muestra lista de backups disponibles):
./.venv-scripts/bin/python3 scripts/panel_admin.py restore-db mitienda

# Pasando el archivo directamente:
./.venv-scripts/bin/python3 scripts/panel_admin.py restore-db mitienda contalibra_20260512_143022.db
```

El proceso: para el contenedor → backup automático del estado actual → restaura → reinicia.

### Ver backups disponibles

```bash
./.venv-scripts/bin/python3 scripts/panel_admin.py list-backups mitienda
```

### El cliente también puede hacer backup/restore

Desde el sistema web: `/config` → pestaña **Datos / Backup**. Puede descargar
la DB y restaurar desde un archivo `.db` previo. Siempre se hace backup
automático antes de cualquier restauración.

---

## Proxy y SSL (Nginx Proxy Manager)

### Setup inicial (una sola vez)

```bash
./.venv-scripts/bin/python3 scripts/npm_setup.py
```

### Al crear un cliente nuevo

Si NPM está configurado, `nuevo_cliente.py` ofrece crear el proxy
automáticamente al final del proceso.

### Crear proxy manualmente para un cliente existente

```bash
./.venv-scripts/bin/python3 scripts/panel_admin.py
# → opción pa (crear proxy NPM)
```

O desde CLI:
```bash
./.venv-scripts/bin/python3 scripts/panel_admin.py npm-crear mitienda
```

### Prerequisito de DNS

Antes de crear el proxy SSL, el dominio del cliente debe apuntar a la IP del
VPS (registro A en su proveedor DNS). Si el dominio no resuelve todavía,
Let's Encrypt fallará al emitir el certificado.

---

## Gestión del estado del servicio

Para corte por falta de pago u otras situaciones:

```bash
# Mostrar estado actual
./.venv-scripts/bin/python3 scripts/panel_admin.py estado mitienda

# Poner en modo aviso (acceso con banner amarillo)
./.venv-scripts/bin/python3 scripts/panel_admin.py pausar mitienda
→ Mensaje para el cliente: Regularizá tu suscripción para evitar la suspensión.

# Suspender acceso completo
./.venv-scripts/bin/python3 scripts/panel_admin.py suspender mitienda
→ Mensaje para el cliente: Servicio suspendido por falta de pago. Contactar a soporte.

# Reactivar
./.venv-scripts/bin/python3 scripts/panel_admin.py activar mitienda
```

El cambio de estado es inmediato — no requiere reiniciar el contenedor.
También se puede gestionar desde dentro del sistema web en `/config` → pestaña **Servicio**.

---

## Website de marketing (contalibra.com.ar)

El website de marketing es un contenedor nginx estático independiente del sistema de clientes.
Se encuentra en `website/` dentro del repositorio.

### Estructura del website

```
website/
├── Dockerfile              ← FROM nginx:1.27-alpine
├── nginx.conf              ← configuración del servidor web
├── docker-compose.yml      ← definición del contenedor
└── public/
    ├── index.html          ← landing page principal
    ├── css/
    │   └── style.css       ← estilos compartidos
    └── docs/               ← documentación pública
        ├── index.html
        ├── primeros-pasos.html
        ├── empresa.html
        ├── usuarios.html
        ├── configuracion.html
        ├── ventas.html
        ├── caja-turnos.html
        ├── facturacion.html
        ├── productos-stock.html
        └── reportes.html
```

### Deploy inicial (primera vez)

```bash
cd /root/contalibra/website

# Construir la imagen
docker build -t contalibra-web:latest .

# Levantar el contenedor
docker compose up -d

# Verificar que está corriendo
docker ps | grep contalibra-web
```

El contenedor escucha en el puerto **8069** y se conecta a la red `stack_stack-net` para que NPM pueda hacer proxy.

### Configurar proxy en Nginx Proxy Manager

1. En NPM, crear un nuevo Proxy Host:
   - **Domain Names:** `contalibra.com.ar`, `www.contalibra.com.ar`
   - **Forward Hostname/IP:** `contalibra-web` (nombre del contenedor)
   - **Forward Port:** `80`
   - **SSL:** habilitar con Let's Encrypt

2. Configurar también el subdominio `docs.contalibra.com.ar` si se desea separar la documentación (opcional — actualmente está bajo `/docs/` en el mismo dominio).

### Actualizar el website

El website es completamente estático. Cualquier cambio de HTML/CSS requiere **reconstruir la imagen**:

```bash
cd /root/contalibra/website

# Traer los últimos cambios del repo
git pull

# Reconstruir y reiniciar
docker compose build
docker compose up -d

# Verificar
docker logs contalibra-web --tail 20
```

No hay reinicio en caliente — siempre se reconstruye porque el contenido se copia durante el `docker build`.

### Rollback del website

Si la nueva versión tiene problemas:

```bash
cd /root/contalibra/website

# Ver historial de imágenes
docker images | grep contalibra-web

# Si tenés una imagen anterior con otro tag:
docker compose down
docker tag contalibra-web:<tag-anterior> contalibra-web:latest
docker compose up -d
```

Para evitar problemas, antes de reconstruir en producción podés hacer:

```bash
docker tag contalibra-web:latest contalibra-web:backup
docker compose build
docker compose up -d
```

Así si algo falla, hacés `docker tag contalibra-web:backup contalibra-web:latest` y levantás la versión anterior.

### Agregar o editar páginas de documentación

1. Editá o creá el archivo HTML en `website/public/docs/`.
2. Si es una página nueva, agregá el link en el sidebar de todas las otras páginas de docs.
3. Reconstruí el contenedor como se indica en "Actualizar el website".

### Verificar que el website está funcionando

```bash
# Desde el VPS
curl -I http://localhost:8069/

# Respuesta esperada: HTTP/1.1 200 OK

# Ver logs de nginx
docker logs contalibra-web --tail 50
```

---

## Estructura de directorios

```
/root/contalibra/
├── web/                        ← aplicación FastAPI
│   ├── app.py                  ← entry point, middleware, rutas
│   ├── auth.py                 ← autenticación con cookies
│   ├── routers/                ← un archivo por módulo
│   └── templates/              ← templates Jinja2
├── scripts/
│   ├── nuevo_cliente.py        ← alta de cliente nuevo
│   ├── panel_admin.py          ← gestión de todos los clientes
│   ├── npm_api.py              ← cliente HTTP para NPM
│   ├── npm_setup.py            ← configuración de NPM
│   └── .npm_config.json        ← credenciales NPM (excluido del repo)
├── clientes/                   ← datos de clientes (excluido del repo)
│   └── <slug>/
│       ├── docker-compose.yml
│       ├── cliente.json        ← nombre, puerto, credenciales admin
│       ├── backups/            ← backups de DB
│       └── data/               ← montado en /app/data
│           ├── contalibra.db   ← base de datos SQLite
│           ├── config.json     ← configuración de la empresa
│           ├── logos/
│           ├── arca_certs/
│           └── backups/        ← backups automáticos (web)
├── database.py                 ← capa de datos
├── config_manager.py           ← lectura/escritura de config.json
├── pdf_generator.py            ← PDFs A4 (facturas, remitos, etc.)
├── ticket_generator.py         ← PDFs angostos para ticketeadoras
├── Dockerfile
├── pyproject.toml             ← dependencias y metadata del paquete
├── OPERACIONES.md              ← este archivo
└── website/                    ← website de marketing (contalibra.com.ar)
    ├── Dockerfile
    ├── nginx.conf
    ├── docker-compose.yml
    └── public/
        ├── index.html          ← landing page
        ├── css/style.css
        └── docs/               ← documentación pública
```
