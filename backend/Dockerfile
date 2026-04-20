# syntax=docker/dockerfile:1
# Mitene FastAPI backend — Cloud Run / Playwright / NotebookLM / ffmpeg
#
# Build: docker build -t mitene-api .
# Run:   docker run -e PORT=8080 -p 8080:8080 mitene-api

FROM python:3.12-slim-bookworm

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

# ffmpeg/ffprobe (thumbnails, duration) + Playwright Chromium system deps
RUN apt-get update -y && apt-get install -y --no-install-recommends \
    ffmpeg \
    libnss3 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libpangocairo-1.0-0 \
    libpango-1.0-0 \
    libcairo2 \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./

RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt \
    && python -m playwright install-deps chromium \
    && python -m playwright install chromium

COPY . .

RUN groupadd --system --gid 1000 mitene \
    && useradd --system --uid 1000 --gid mitene --home /app --shell /usr/sbin/nologin mitene \
    && mkdir -p /app/uploads /app/outputs /home/mitene/.notebooklm \
    && chown -R mitene:mitene /app /home/mitene

USER mitene

EXPOSE 8080

ENV PORT=8080

# Health: /docs (OpenAPI) or any route; Cloud Run uses TCP + optional startup probe
CMD ["sh", "-c", "exec uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080}"]
