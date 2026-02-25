# ============================================
# STAGE 1: Builder — instala dependencias
# ============================================
# Multi-stage build: una etapa para instalar, otra para ejecutar.
# Así la imagen final es más pequeña (no incluye herramientas de build).
FROM python:3.12-slim AS builder

WORKDIR /app

# Instalar dependencias del sistema que algunas librerías Python necesitan
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc libpq-dev && \
    rm -rf /var/lib/apt/lists/*

# Copiar solo el archivo de dependencias primero.
# Docker cachea capas: si pyproject.toml no cambia, no reinstala.
COPY pyproject.toml ./

# Instalar dependencias Python
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir .

# ============================================
# STAGE 2: Runtime — imagen final ligera
# ============================================
FROM python:3.12-slim AS runtime

WORKDIR /app

# Librería de PostgreSQL necesaria en runtime
RUN apt-get update && \
    apt-get install -y --no-install-recommends libpq5 curl && \
    rm -rf /var/lib/apt/lists/*

# Crear usuario no-root (seguridad: nunca correr como root)
RUN useradd --create-home --shell /bin/bash appuser

# Copiar dependencias instaladas del builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copiar código de la aplicación
COPY . .

# Cambiar a usuario no-root
USER appuser

# Puerto de la API
EXPOSE 8000

# Comando por defecto: uvicorn con hot-reload (dev)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]