# ============================================
# LeadForge — Makefile
# ============================================
# Atajos para no escribir comandos largos de Docker.
# Uso: make <comando>

# Variable para el archivo docker-compose
DC = docker compose -f docker/docker-compose.yml

# -------------------------------------------
# Docker
# -------------------------------------------

## Levantar todos los servicios en background
up:
	$(DC) up -d --build

## Parar todos los servicios
down:
	$(DC) down

## Parar y borrar volúmenes (reset completo de datos)
reset:
	$(DC) down -v

## Ver estado de los servicios
ps:
	$(DC) ps

## Ver logs de todos los servicios (en vivo)
logs:
	$(DC) logs -f

## Ver logs solo de la API
logs-api:
	$(DC) logs -f api

## Ver logs solo de PostgreSQL
logs-db:
	$(DC) logs -f postgres

## Reiniciar solo la API (útil cuando cambias config)
restart-api:
	$(DC) restart api

# -------------------------------------------
# Base de datos
# -------------------------------------------

## Conectarse a PostgreSQL por consola
db-shell:
	$(DC) exec postgres psql -U leadforge -d leadforge

## Conectarse a Redis por consola
redis-shell:
	$(DC) exec redis redis-cli

# -------------------------------------------
# Tests y calidad
# -------------------------------------------

## Ejecutar tests dentro del contenedor
test:
	$(DC) exec api pytest -v

## Ejecutar linter (ruff)
lint:
	$(DC) exec api ruff check app/

## Formatear código (ruff)
format:
	$(DC) exec api ruff format app/

# -------------------------------------------
# Ayuda
# -------------------------------------------

## Mostrar todos los comandos disponibles
help:
	@echo.
	@echo  LeadForge - Comandos disponibles:
	@echo  ================================
	@echo  make up          - Levantar servicios
	@echo  make down        - Parar servicios
	@echo  make reset       - Parar y borrar datos
	@echo  make ps          - Ver estado
	@echo  make logs        - Ver todos los logs
	@echo  make logs-api    - Ver logs de la API
	@echo  make logs-db     - Ver logs de PostgreSQL
	@echo  make restart-api - Reiniciar la API
	@echo  make db-shell    - Consola PostgreSQL
	@echo  make redis-shell - Consola Redis
	@echo  make test        - Ejecutar tests
	@echo  make lint        - Pasar linter
	@echo  make format      - Formatear codigo
	@echo.

.PHONY: up down reset ps logs logs-api logs-db restart-api db-shell redis-shell test lint format help