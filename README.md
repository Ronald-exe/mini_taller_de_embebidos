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
sudo usermod -aG docker ronald_soc
```

```bash
groups ronald_soc
```

---

## RETO 2: Primer Contenedor

```bash
docker --version
docker run hello-world
```

---

## Docker Hub: Tags y Versiones

```bash
docker pull postgres:latest
docker pull postgres:17
docker pull rust:1.87-bookworm
docker pull openproject/openproject:17-slim
```

---

## Docker Hub: docker pull

```bash
docker pull ubuntu:24.04
docker images
```

---

## Docker Hub: docker push

```bash
docker login
docker build --network=host -t clothing-detector .
docker tag clothing-detector ronaldsoc/clothing-detector:1.0
docker push ronaldsoc/clothing-detector:1.0
```

---

## Dockerfile: FROM y RUN

```dockerfile
FROM rust:1.87-bookworm

RUN apt-get update && apt-get install -y \
    libopencv-dev \
    clang \
    cmake
```

---

## Dockerfile: COPY y WORKDIR

```dockerfile
COPY src/ /app/src/
COPY Cargo.toml /app/
WORKDIR /app
```

---

## Dockerfile: EXPOSE

```dockerfile
EXPOSE 80
```

---

## Dockerfile: CMD

```dockerfile
CMD ["cargo", "run", "--release"]
```

---

## Dockerfile: Variables de Entorno

```dockerfile
ENV APP_ENV=production
ENV DATABASE_URL=postgres://db:5432/myapp
```

```bash
docker run -e DATABASE_URL=postgres://... mi-app
```

---

## Paso 1: Clonar OpenProject

```bash
git clone https://github.com/opf/openproject-deploy.git quickstart
cd quickstart
cp .env.example .env
```

---

## Paso 2: Docker Compose

```bash
docker compose version
sudo apt install -y docker-compose-v2
```

---

## RETO 3: Desplegar OpenProject

```bash
# Paso 1 - Levantar
docker compose up -d
```

```bash
# Paso 2 - Corregir permisos (en otra terminal)
docker compose exec --user root web bash -c "mkdir -p /var/openproject/assets/files && chown -R app:app /var/openproject/assets"
```

```bash
# Paso 3 - Monitorear el seeder
docker compose logs seeder -f | grep -v "ActiveJob\|GoodJob\|Journals"
```

> Listo cuando veas: `*** Seeding MCP configuration`
> Credenciales: **admin** / **admin**

---

## RETO 6: Demostrar Efimeridad

```bash
docker run --rm alpine sh -c "echo 'Dato Critico' > /file.txt && cat /file.txt"
docker run --rm alpine cat /file.txt
```

---

## Redes Internas

```bash
docker network ls
docker stats
docker compose exec web whoami
```

---

## Docker Networking

```bash
docker network ls
docker network inspect quickstart_default
docker network create mi-red
docker network connect mi-red mi-contenedor
```

---

## Ciclo de Vida

```bash
docker compose stop
docker compose down
docker compose up -d
```

---

## Higiene del Sistema

```bash
docker system prune
```

---

## LABORATORIO FINAL

### Paso 0: Registrar en OpenProject
> Entrá a http://localhost:8080 → Proyecto "Taller Docker 2026" → New Work Package → "Configurar entorno Rust+OpenCV" → In progress

---

### Paso 1: Clonar desde GitHub

```bash
git clone https://github.com/Ronald-exe/Embedded_System
cd Embedded_System/proyecto_openCV
```

```bash
cat > .dockerignore << 'EOF'
target/
.git/
*.log
EOF
```

---

### Paso 2: Crear el Dockerfile

```bash
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
```

```bash
git add Dockerfile .dockerignore
git commit -m "Add Docker environment"
git push
```

---

### Paso 3: Construir y publicar

```bash
docker build --network=host -t mi-entorno-rust .
```

```bash
docker login
docker tag mi-entorno-rust ronaldsoc/mi-entorno-rust:1.0
docker push ronaldsoc/mi-entorno-rust:1.0
```

---

### Paso 4: Entrar al contenedor

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

```bash
# Dentro del contenedor
cargo build
./target/debug/proyecto_openCV --video /videos/v1.mp4
```

---

### Paso 5: El compañero se une

```bash
git clone https://github.com/Ronald-exe/Embedded_System
cd Embedded_System/proyecto_openCV
docker pull ronaldsoc/mi-entorno-rust:1.0
xhost +local:docker
docker run -it --rm --network=host \
  -e DISPLAY=$DISPLAY \
  -v /tmp/.X11-unix:/tmp/.X11-unix \
  -v $(pwd):/app \
  -v $HOME/Pictures:/videos \
  ronaldsoc/mi-entorno-rust:1.0 bash
```

---

### Paso 6: Cerrar en OpenProject
> http://localhost:8080 → Work Package "Configurar entorno Rust+OpenCV" → Closed → Comentario: "Imagen publicada como ronaldsoc/mi-entorno-rust:1.0"

---

## Limpieza Final

```bash
docker image rm mi-entorno-rust
docker system prune
```
