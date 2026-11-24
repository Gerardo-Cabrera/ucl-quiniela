FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Correr sin privilegios (en dev el volumen montado solo requiere lectura).
RUN useradd --create-home appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Comando por defecto = el de producción, para que la imagen sea correcta aunque nadie
# le pase un comando (p. ej. un servicio nuevo en un PaaS con el "Start Command" vacío):
# - --proxy-headers --forwarded-allow-ips='*': en producción el backend va SIEMPRE detrás
#   de un proxy (el de la plataforma, o nginx en docker-compose.prod.yml). Sin esto la IP
#   del cliente sería la del proxy y TODOS los participantes compartirían un único cupo
#   en cada límite de peticiones (también el de login), además de generar redirecciones
#   en http. No expongas esta imagen directamente a Internet sin un proxy delante: un
#   cliente podría falsear su IP en la cabecera.
# - ${PORT:-8000}: las plataformas inyectan el puerto en PORT; en local, 8000.
# - exec: uvicorn sustituye al shell y recibe las señales de parada.
# El compose de desarrollo lo sustituye por uno con --reload y sin cabeceras de proxy.
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips='*'"]
