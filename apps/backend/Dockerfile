FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg libglib2.0-0 libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY apps/backend/requirements.txt /app/apps/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/apps/backend/requirements.txt

COPY ai /app/ai
COPY apps /app/apps
COPY scripts /app/scripts
COPY docs /app/docs
COPY tests /app/tests
COPY pytest.ini /app/pytest.ini
COPY data/page_images /app/data/page_images

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --retries=3 CMD python -c "import os, urllib.request; urllib.request.urlopen('http://127.0.0.1:%s/health' % os.environ.get('PORT', '8000'), timeout=3).read()"

CMD ["sh", "-c", "uvicorn apps.backend.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
