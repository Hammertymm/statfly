# Fly Intelligence Platform — cloud deployment
FROM python:3.12-slim

WORKDIR /app

# Copy engine + FlyTime JSON tables (needed for scoring)
COPY flytime-engine/ ./flytime-engine/
COPY *-flytime-v1.json ./

ENV PYTHONUNBUFFERED=1
ENV FLYTIME_DB_PATH=/data/flytime_engine.db
ENV HOST=0.0.0.0
ENV PORT=8787
ENV FEATURE_EXPORT_DIR=/data/exports

RUN mkdir -p /data/exports

WORKDIR /app/flytime-engine

EXPOSE 8787

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8787/api/health')" || exit 1

CMD ["python", "run_platform.py"]
