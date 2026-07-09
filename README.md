# 🏆 UCL Quiniela App

[![CI](https://github.com/Gerardo-Cabrera/ucl-quiniela/actions/workflows/ci.yml/badge.svg)](https://github.com/Gerardo-Cabrera/ucl-quiniela/actions/workflows/ci.yml)

Aplicación de quiniela basada en la UEFA Champions League con sistema de puntuación por fases.

## Stack

| Capa | Tecnología |
|------|-----------|
| Frontend | React 18 + Vite + TypeScript |
| Estilos | Tailwind CSS |
| Estado | Zustand + React Query |
| Backend | FastAPI + Python 3.12 |
| Base de Datos | PostgreSQL |
| ORM | SQLAlchemy 2.0 (async) |
| Migraciones | Alembic |
| Scheduler | APScheduler (sync UCL data) |
| API Fútbol | API-Football (RapidAPI) |

## Estructura

```
ucl-quiniela/
├── backend/        # FastAPI
├── frontend/       # React + Vite
├── docker-compose.yml
└── README.md
```

## Quick Start

**Requisito**: PostgreSQL instalado y corriendo en el host (la app usa la
instancia nativa del sistema, no un contenedor — los datos no dependen de Docker).

### 1. Crear la base de datos (una sola vez)

```bash
psql -d postgres -c "CREATE ROLE quiniela LOGIN PASSWORD 'quiniela_pass'"
psql -d postgres -c "CREATE DATABASE ucl_quiniela OWNER quiniela"
```

### 2. Configurar variables de entorno

```bash
# Backend
cp backend/.env.example backend/.env
# Edita backend/.env con tus credenciales (API_FOOTBALL_KEY, etc.)

# Frontend
cp frontend/.env.example frontend/.env
```

### 3. Levantar con Docker Compose

```bash
docker compose up -d
```

Las migraciones se aplican automáticamente al arrancar el backend
(que corre con `network_mode: host` para alcanzar el PostgreSQL local).

> **Respaldo**: `pg_dump -h localhost -U quiniela ucl_quiniela > backup.sql`

### 4. Crear el primer administrador (opcional)

Los endpoints admin (forzar sync, calcular Top 8) requieren un usuario con
`is_admin`. Tras registrarte en la app:

```bash
psql -d ucl_quiniela -c "UPDATE users SET is_admin = true WHERE email = 'tu@email.com';"
```

### 5. Levantar manualmente (opcional, no recomendado)

> El proyecto está dockerizado: la forma soportada es `docker compose`. Este
> modo manual instala dependencias en el host (venv de Python, node_modules) y
> solo se documenta como último recurso si no se dispone de Docker.

**Backend:**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

## URLs

| Servicio | URL |
|---------|-----|
| Frontend | http://localhost:5173 |
| Backend API | http://localhost:8000 |
| Swagger Docs | http://localhost:8000/docs |
| ReDoc | http://localhost:8000/redoc |

## Producción

```bash
# 1. Contraseña de la BD (raíz del proyecto)
echo "POSTGRES_PASSWORD=una-contraseña-fuerte" > .env

# 2. Configura backend/.env: SECRET_KEY propio, API_FOOTBALL_KEY, etc.
#    (con APP_ENV=production el SECRET_KEY por defecto bloquea el arranque)

# 3. Levantar (migraciones incluidas; frontend compilado servido por nginx en :80)
docker compose -f docker-compose.prod.yml up -d --build
```

## Tests

Dentro del contenedor (no requiere instalar nada en el host):

```bash
docker compose exec backend pytest
```

## Revisión de PRs (IA)

Los PR se revisan con [PR-Agent](https://github.com/qodo-ai/pr-agent) (open-source)
usando el **free tier** de Google Gemini (sin coste). Para activarlo:

1. Crea una API key gratuita en [Google AI Studio](https://aistudio.google.com/apikey).
2. Añádela como **secret** del repositorio `GEMINI_API_KEY`
   (Settings → Secrets and variables → Actions → New repository secret).

Sin ese secret, el workflow **se omite** (no falla). Ya activo, al abrir un PR
genera resumen, revisión y sugerencias, y responde a comandos en los comentarios:
`/review`, `/describe`, `/improve`, `/ask <pregunta>`.

## Sistema de Puntuación

### Fase de Liga
| Acierto | Puntos |
|---------|--------|
| Victoria | 5 pts |
| Empate | 6 pts |
| 1er Gol (primer goleador) | 3 pts |
| Resultado Exacto | 8 pts |

### A partir de Octavos
| Acierto | Puntos |
|---------|--------|
| Victoria | 8 pts |
| Empate | 9 pts |
| 1er Gol (primer goleador) | 5 pts |
| Resultado Exacto | 11 pts |

### Top 8

Los 8 equipos que terminan en las posiciones **1-8 de la fase de liga** y pasan
directo a octavos de final (sin jugar la ronda de playoff).

| Acierto | Puntos |
|---------|--------|
| Equipo (sin importar posición) | 3 pts |
| Equipo en posición exacta | 5 pts |
