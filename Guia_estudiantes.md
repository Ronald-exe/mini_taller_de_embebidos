# Reto Final: Flujo Profesional con Docker
**Taller de Sistemas Embebidos — 2026**

> ⚠️ **Copiá los comandos desde este archivo, no desde el PDF.** Los comandos del PDF pueden tener espacios invisibles que rompen la ejecución.

---

## Objetivo

Instalar Docker desde cero, desplegar OpenProject, dockerizar tu proyecto Rust+OpenCV y tu entorno Yocto/Poky, y publicar ambas imágenes en Docker Hub para que tu compañero las use sin instalar nada.

---

## Paso 1: Instalar Docker Engine

```bash
sudo apt update
sudo apt-get purge -y containerd.io
sudo apt install -y docker.io
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -aG docker $USER
```

> ⚠️ **CRÍTICO:** Cerrá la sesión completamente y volvé a entrar. Sin esto los comandos de Docker fallan con errores de permisos.

Verificá que quedó bien:

```bash
groups $USER
```

Deberías ver `docker` en la lista. Luego verificá que Docker funciona:

```bash
docker --version
docker run hello-world
```

Si ves `Hello from Docker!` el motor está funcionando correctamente.

---

## Paso 2: Instalar Docker Compose

```bash
docker compose version
```

Si el comando falla o no existe:

```bash
sudo apt install -y docker-compose-v2
docker compose version
```

Deberías ver algo como `Docker Compose version v2.x.x`.

---

## Paso 3: Desplegar OpenProject

### Clonar el repositorio oficial

```bash
cd ~/Documents
git clone https://github.com/opf/openproject-deploy.git quickstart
cd quickstart
cp .env.example .env
```

### Levantar los contenedores

```bash
docker compose up -d
```

### Corregir permisos del seeder (en otra terminal)

```bash
cd ~/Documents/quickstart
docker compose exec --user root web bash -c "mkdir -p /var/openproject/assets/files && chown -R app:app /var/openproject/assets"
```

> ⚠️ Sin este paso el seeder falla y la cuenta `admin` nunca se inicializa correctamente.

### Monitorear hasta que esté listo

```bash
docker compose logs seeder -f | grep -v "ActiveJob\|GoodJob\|Journals"
```

> ✅ Listo cuando veas: `*** Seeding MCP configuration`
> Esto puede tardar entre 5 y 10 minutos.

### Acceder a OpenProject

Abrí el navegador en: **http://localhost:8080**

- **Usuario:** `admin`
- **Contraseña:** `admin`

---

## Paso 4: Registrar tu tarea en OpenProject

Antes de escribir una sola línea de código:

1. Iniciá sesión en `http://localhost:8080`
2. Creá un proyecto nuevo: **"Reto Docker — Tu Nombre"**
3. Andá a **Work packages** en el menú izquierdo
4. Hacé clic en **+ Create** y creá la tarea: **"Dockerizar entorno de desarrollo"**
5. Asignátela a vos mismo, poné fecha límite y cambiá el estado a **In progress**

---

## Parte A: Dockerizar tu Proyecto Rust + OpenCV

### A.1 — Crear cuenta en Docker Hub

Si no tenés cuenta, creála gratis en [hub.docker.com](https://hub.docker.com). Iniciá sesión desde la terminal:

```bash
docker login
```

### A.2 — Ubicarse en la carpeta del proyecto

```bash
cd ~/ruta/a/tu/proyecto/rust
ls    # Deberías ver Cargo.toml, src/, etc.
```

### A.3 — Crear el `.dockerignore`

> ⚠️ **Hacé esto ANTES del build.** La carpeta `target/` de Rust puede pesar más de 500MB. Sin este archivo Docker la manda toda al motor de construcción y el build tarda horas.

```bash
cat > .dockerignore << 'EOF'
target/
.git/
*.log
*.tmp
EOF
```

Verificá que se creó bien:

```bash
cat .dockerignore
```

### A.4 — Crear el Dockerfile

```bash
cat > Dockerfile << 'EOF'
FROM rust:1.87-bookworm

RUN apt-get update && apt-get install -y \
    libopencv-dev \
    clang \
    libclang-dev \
    cmake \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
EOF
```

> ℹ️ Si tu proyecto necesita librerías adicionales, agregálas en el bloque `apt-get install`. Si usás una versión diferente de Rust, cambiá `rust:1.87-bookworm`.

### A.5 — Construir la imagen

```bash
docker build --network=host -t mi-entorno-rust .
```

> ⚠️ Este paso tarda entre 10 y 20 minutos la primera vez. Si parece que se congeló, verificá en otra terminal con `docker stats`. Si hay actividad de CPU o red, el build sigue vivo.

Verificá que la imagen existe:

```bash
docker images | grep mi-entorno-rust
```

### A.6 — Probar que el entorno funciona

```bash
xhost +local:docker
```

```bash
docker run -it --rm --network=host \
  -e DISPLAY=$DISPLAY \
  -v /tmp/.X11-unix:/tmp/.X11-unix \
  -v $(pwd):/app \
  -v $HOME/Pictures:/videos \
  mi-entorno-rust bash
```

Dentro del contenedor:

```bash
cargo build
./target/debug/NOMBRE_DE_TU_BINARIO --video /videos/tu_video.mp4
exit
```

> ℹ️ El nombre del binario está en tu `Cargo.toml` bajo `[package] name = "..."`. Verificálo con `cat Cargo.toml`.

### A.7 — Subir el Dockerfile a GitHub

```bash
git add Dockerfile .dockerignore
git commit -m "Add Docker environment for Rust+OpenCV"
git push
```

### A.8 — Publicar la imagen en Docker Hub

```bash
docker tag mi-entorno-rust TU_USUARIO/mi-entorno-rust:1.0
docker push TU_USUARIO/mi-entorno-rust:1.0
```

> Reemplazá `TU_USUARIO` con tu usuario real de Docker Hub.

> ✅ Verificación: Andá a `hub.docker.com`, iniciá sesión y deberías ver tu imagen publicada.

---

## Parte B: Dockerizar tu Entorno Yocto/Poky

### B.1 — Crear la carpeta del reto

```bash
mkdir -p ~/reto-yocto-docker
cd ~/reto-yocto-docker
```

### B.2 — Verificar tu versión de Poky

```bash
ls ~/Documents/
cd ~/Documents/TU_CARPETA_POKY
git branch
```

Anotá la rama que tenés (por ejemplo: `scarthgap`, `kirkstone`, `nanbield`). La usarás para etiquetar tu imagen.

### B.3 — Crear el `.dockerignore`

> ⚠️ **MUY IMPORTANTE:** La carpeta `build/` de Yocto puede pesar más de 100GB. Las carpetas `downloads/` y `sstate-cache/` también son muy pesadas. Sin este archivo el build fallará o tardará horas.

```bash
cat > .dockerignore << 'EOF'
build/
.git/
downloads/
sstate-cache/
*.log
*.tmp
EOF
```

### B.4 — Crear el Dockerfile para Yocto

```bash
cat > Dockerfile << 'EOF'
FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    gawk \
    wget \
    git \
    diffstat \
    unzip \
    texinfo \
    gcc \
    build-essential \
    chrpath \
    socat \
    cpio \
    python3 \
    python3-pip \
    python3-pexpect \
    xz-utils \
    debianutils \
    iputils-ping \
    python3-git \
    python3-jinja2 \
    libegl1-mesa \
    libsdl1.2-dev \
    xterm \
    python3-subunit \
    mesa-common-dev \
    zstd \
    liblz4-tool \
    file \
    locales \
    && locale-gen en_US.UTF-8 \
    && rm -rf /var/lib/apt/lists/*

ENV LANG=en_US.UTF-8

RUN useradd -m -s /bin/bash yocto

WORKDIR /yocto
USER yocto
EOF
```

> ℹ️ Se usa `ubuntu:22.04` porque es compatible con la mayoría de versiones modernas de Yocto. Si tu versión de Poky es muy antigua (antes de Kirkstone), puede que necesites `ubuntu:20.04`.

### B.5 — Construir la imagen

```bash
docker build --network=host -t yocto-env .
```

Verificá que la imagen existe:

```bash
docker images | grep yocto-env
```

### B.6 — Entrar al contenedor con Poky montado y cocinar

```bash
docker run -it --rm \
  -v ~/Documents/TU_CARPETA_POKY:/yocto/poky \
  yocto-env bash
```

Una vez dentro del contenedor (el prompt cambia a `yocto@...`):

```bash
cd /yocto/poky
source oe-init-build-env build-docker
```

Verificá que el entorno está activo:

```bash
bitbake -e | grep ^TMPDIR
```

Si muestra una ruta, el entorno está listo. Ahora podés cocinar:

```bash
bitbake core-image-minimal
```

> ℹ️ **¿Por qué funciona cocinar dentro del contenedor?** Porque montaste tu carpeta de Poky real como volumen con `-v`. El resultado de la compilación se guarda en `TU_CARPETA_POKY/build-docker/tmp/` en tu disco real. Si el contenedor muere, la compilación no se pierde.

> ⚠️ **La compilación completa tarda varias horas.** Es completamente normal. Si solo querés verificar que el entorno funciona, el comando `bitbake -e` es suficiente.

### B.7 — Publicar la imagen en Docker Hub

```bash
# Salir del contenedor primero
exit

# Etiquetar con tu usuario y tu version de Poky
docker tag yocto-env TU_USUARIO/yocto-env:TU_VERSION_POKY
docker push TU_USUARIO/yocto-env:TU_VERSION_POKY
```

Por ejemplo:

```bash
docker tag yocto-env ronaldsoc/yocto-env:scarthgap
docker push ronaldsoc/yocto-env:scarthgap
```

---

## Parte C: Tu compañero replica sin instalar nada

Tu compañero solo necesita Docker instalado (Pasos 1 y 2). Nada más.

### Usar tu entorno Rust+OpenCV

```bash
git clone TU_REPO_GITHUB
cd TU_REPO
docker pull TU_USUARIO/mi-entorno-rust:1.0
xhost +local:docker
docker run -it --rm --network=host \
  -e DISPLAY=$DISPLAY \
  -v /tmp/.X11-unix:/tmp/.X11-unix \
  -v $(pwd):/app \
  -v $HOME/Pictures:/videos \
  TU_USUARIO/mi-entorno-rust:1.0 bash
```

### Usar tu entorno Yocto

```bash
docker pull TU_USUARIO/yocto-env:TU_VERSION_POKY

docker run -it --rm \
  -v ~/Documents/TU_CARPETA_POKY:/yocto/poky \
  TU_USUARIO/yocto-env:TU_VERSION_POKY bash
```

---

## Paso Final: Cerrar el ciclo en OpenProject

1. Andá a `http://localhost:8080`
2. Abrí el Work Package **"Dockerizar entorno de desarrollo"**
3. Cambiá el estado a **Closed**
4. Agregá un comentario con las URLs de tus imágenes en Docker Hub

---

## Entregables del Reto

| # | Entregable | Verificación |
|---|-----------|-------------|
| 1 | OpenProject corriendo en `localhost:8080` | Demo en vivo |
| 2 | Imagen Rust+OpenCV publicada en Docker Hub | URL pública |
| 3 | Imagen Yocto publicada en Docker Hub | URL con tag de versión |
| 4 | `cargo build` dentro del contenedor | Demo: compilación sin errores |
| 5 | `bitbake -e` dentro del contenedor | Demo: entorno activo |
| 6 | Compañero usa tus imágenes con `docker pull` | Demo en vivo |
| 7 | Work Package cerrado en OpenProject | Captura de pantalla |

---

> ✅ **Criterio de éxito:** Un compañero con Docker instalado debe poder compilar tu proyecto Rust+OpenCV y usar tu entorno Yocto en menos de 5 minutos, con solo `docker pull`. Sin instalar dependencias. Sin conflictos de versiones. Eso es Docker en la industria real.
>
> ## Buenas Prácticas
 
**Siempre usá `.dockerignore` antes de cualquier build.**
Sin él, Docker manda todo el directorio al motor — incluyendo `target/` de Rust (500MB+) o `build/` de Yocto (100GB+). El build se vuelve lento o directamente falla.
 
**Nunca uses solo el tag `latest` en producción.**
`latest` cambia con cada nuevo push y hace imposible reproducir un entorno exacto. Siempre usá versiones específicas como `:1.0` o `:scarthgap`.
 
```bash
# Mal
docker tag mi-imagen tuusuario/mi-imagen:latest
 
# Bien
docker tag mi-imagen tuusuario/mi-imagen:1.0
```
 
**Nunca subas el archivo `.env` a GitHub.**
El `.env` contiene contraseñas y secretos. Agregálo al `.gitignore`:
 
```bash
echo ".env" >> .gitignore
```
 
**Corré procesos como usuario no-root dentro del contenedor.**
El Dockerfile de Yocto ya crea un usuario `yocto` para esto. Correr como root dentro de un contenedor es un riesgo de seguridad — si el contenedor es comprometido, el atacante tiene acceso root al sistema.
 
**Hacé limpieza periódica del sistema.**
Cada build genera capas e imágenes intermedias que acumulan espacio:
 
```bash
# Ver cuánto espacio está usando Docker
docker system df
 
# Limpiar todo lo que no está en uso
docker system prune
 
# Limpiar incluyendo imágenes sin tag
docker system prune -a
```
 
**Montá volúmenes para datos que no deben perderse.**
El `build/` de Yocto, el `target/` de Rust y cualquier dato que querés conservar deben estar en volúmenes o bind mounts (`-v`), nunca solo dentro del contenedor.
 
---
 
## Errores Comunes y Soluciones
 
**Error: `Permission denied` al correr docker**
```
permission denied while trying to connect to the Docker daemon socket
```
Causa: tu usuario no está en el grupo `docker`.
Solución:
```bash
sudo usermod -aG docker $USER
# Cerrá sesión y volvé a entrar
```
 
---
 
**Error: Seeder de OpenProject falla con `Permission denied`**
```
Errno::EACCES: Permission denied @ dir_s_mkdir - /var/openproject/assets/files
```
Causa: el volumen de OpenProject no tiene los permisos correctos para el usuario `app`.
Solución:
```bash
docker compose exec --user root web bash -c "mkdir -p /var/openproject/assets/files && chown -R app:app /var/openproject/assets"
docker compose restart seeder
```
 
---
 
**Error: Build pesa 500MB o más**
Causa: no existe el `.dockerignore` y Docker está mandando `target/` al motor.
Solución: creá el `.dockerignore` antes del build:
```bash
cat > .dockerignore << 'EOF'
target/
.git/
*.log
EOF
```
 
---
 
**Error: Build de Yocto falla o tarda horas**
Causa: no existe el `.dockerignore` y Docker intenta copiar `build/`, `downloads/` o `sstate-cache/`.
Solución:
```bash
cat > .dockerignore << 'EOF'
build/
.git/
downloads/
sstate-cache/
*.log
EOF
```
 
---
 
**Error: `docker push` falla con `unauthorized`**
```
unauthorized: authentication required
```
Causa: no iniciaste sesión en Docker Hub.
Solución:
```bash
docker login
```
 
---
 
**Error: `tag does not exist`**
```
tag does not exist: tuusuario/mi-imagen:1.0
```
Causa: hiciste `docker push` antes de hacer `docker tag`.
Solución: siempre hacer el tag primero:
```bash
docker tag mi-imagen tuusuario/mi-imagen:1.0
docker push tuusuario/mi-imagen:1.0
```
 
---
 
**Error: carpeta no montada dentro del contenedor**
```
bash: cd: /yocto/poky: No such file or directory
```
Causa: el volumen fue escrito sin los dos puntos `:` que separan la ruta real de la ruta dentro del contenedor.
```bash
# Mal — falta el :
-v ~/Documents/poky-scarthgap/yocto/poky
 
# Bien
-v ~/Documents/poky-scarthgap:/yocto/poky
```
 
---
 
**Error: comandos con espacios rotos al copiar del PDF**
```
docker: unknown flag: --network=host
```
Causa: el PDF introduce espacios invisibles o guiones especiales al copiar.
Solución: siempre copiá los comandos desde el archivo `.md` en el repositorio, nunca desde el PDF.
