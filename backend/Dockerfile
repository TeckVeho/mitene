# syntax=docker/dockerfile:1
# Mitene FastAPI backend — Cloud Run / Playwright / NotebookLM / ffmpeg
#
# Build: docker build -t mitene-api .
# Run:   docker run -e PORT=8080 -p 8080:8080 mitene-api

FROM python:3.12-slim-bookworm

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# ffmpeg/ffprobe (thumbnails, duration) + git (wiki sync)
RUN apt-get update -y && apt-get install -y --no-install-recommends \
    ffmpeg \
    git \
    openssh-client \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./

RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

COPY . .

RUN groupadd --system --gid 1000 mitene \
    && useradd --system --uid 1000 --gid mitene --home /app --shell /usr/sbin/nologin mitene \
    && mkdir -p /app/uploads /app/outputs /app/.notebooklm \
    && chown -R mitene:mitene /app /home/mitene

USER mitene

EXPOSE 8080

ENV PORT=8080

# Health: /docs (OpenAPI) or any route; Cloud Run uses TCP + optional startup probe
CMD ["sh", "-c", "exec uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080}"]
