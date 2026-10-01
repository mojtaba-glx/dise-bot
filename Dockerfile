FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir --require-hashes -r requirements.txt
RUN pip install --no-cache-dir "telethon==1.45.0"

COPY src/ ./src/
ENV PYTHONPATH=/app/src
RUN useradd --create-home --uid 10001 bot \
    && mkdir -p /data \
    && chown bot:bot /data

USER bot
CMD ["python", "-m", "dise_bot"]
