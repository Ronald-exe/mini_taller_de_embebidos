# Comandos del Taller Docker 2026
> Copiá desde aquí, no desde el PDF.

---

## RETO 1: Instalación de Docker Engine

```bash
sudo apt update
sudo apt-get purge -y containerd.io
sudo apt install -y docker.io
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -aG docker $USER
```

> Cerrá sesión y volvé a entrar. Verificá con: `groups $USER`

---

## RETO 2: Primer Contenedor

```bash
docker --version
docker run hello-world
```

---

## RETO 3: Desplegar OpenProject

```bash
# Paso 1 - Clonar el repositorio
git clone https://github.com/opf/openproject-deploy.git quickstart
cd quickstart
cp .env.example .env

# Paso 2 - Levantar los contenedores
docker compose up -d

# Paso 3 - Corregir permisos (en otra terminal)
docker compose exec --user root web bash -c "mkdir -p /var/openproject/assets/files && chown -R app:app /var/openproject/assets"

# Paso 4 - Monitorear el seeder
docker compose logs seeder -f | grep -v "ActiveJob\|GoodJob\|Journals"
```

> Listo cuando veas: `*** Seeding MCP configuration`
> Credenciales: **admin** / **admin**

---

## RETO 6: Demostrar efimeridad de contenedores

```bash
docker run --rm alpine sh -c "echo 'Dato Critico' > /file.txt && cat /file.txt"
docker run --rm alpine cat /file.txt
```

---

## Redes

```bash
docker network ls
docker network inspect quickstart_default
```

---

## Monitoreo

```bash
docker compose ps
docker stats
docker compose exec web whoami
```

---

## Ciclo de vida

```bash
docker compose stop
docker compose down
docker compose up -d
```

---

## Higiene del sistema

```bash
docker system prune
```

---

## Laboratorio Rust + OpenCV

```bash
# Crear .dockerignore
cat > .dockerignore << 'EOF'
target/
.git/
*.log
EOF

# Crear Dockerfile
cat > Dockerfile << 'EOF'
FROM rust:1.87-bookworm

RUN apt-get update && apt-get install -y \
    libopencv-dev \
    clang \
    libclang-dev \
    cmake \
    pkg-config

WORKDIR /app
EOF

# Construir imagen
docker build --network=host -t mi-entorno-rust .

# Habilitar pantalla
xhost +local:docker

# Entrar al contenedor
docker run -it --rm --network=host \
  -e DISPLAY=$DISPLAY \
  -v /tmp/.X11-unix:/tmp/.X11-unix \
  -v $(pwd):/app \
  -v $HOME/Pictures:/videos \
  mi-entorno-rust bash
```

> Dentro del contenedor:
> ```bash
> cargo build
> ./target/debug/proyecto_openCV --video /videos/v1.mp4
> ```

---

## Limpieza final

```bash
docker image rm mi-entorno-rust
docker system prune
```
