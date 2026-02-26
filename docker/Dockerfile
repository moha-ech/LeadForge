# ============================================
# LeadForge — Dockerfile (Desarrollo)
# ============================================
# Imagen simple para desarrollo con hot-reload.
# En producción usaríamos multi-stage.
FROM python:3.12-slim

WORKDIR /app

# Dependencias del sistema
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc libpq-dev curl && \
    rm -rf /var/lib/apt/lists/*

# Copiar dependencias e instalar
COPY pyproject.toml ./
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir .

# Copiar código
COPY . .

# Añadir /app al PYTHONPATH para que Python encuentre 'app' como módulo
ENV PYTHONPATH=/app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]