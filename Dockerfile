# Arya Bank sandbox: payments API (8000) + net banking web app (4173) in one image.
#
#   docker run --rm -p 8000:8000 -p 4173:4173 ghcr.io/byshivam/arya-bank-sandbox
#   docker run --rm -p 8000:8000 -p 4173:4173 -e ARYA_MODE=clean ghcr.io/byshivam/arya-bank-sandbox

FROM node:22-bookworm-slim AS node

FROM python:3.11-slim

LABEL org.opencontainers.image.title="arya-bank-sandbox" \
      org.opencontainers.image.description="A fake bank with planted bugs, for practising API, UI and database testing" \
      org.opencontainers.image.source="https://github.com/byshivam/arya-bank-sandbox" \
      org.opencontainers.image.licenses="MIT"

COPY --from=node /usr/local/bin/node /usr/local/bin/node

WORKDIR /app
COPY services/payments-api/requirements.txt services/payments-api/requirements.txt
RUN pip install --no-cache-dir -r services/payments-api/requirements.txt

COPY services services
COPY run_sandbox.py .

RUN useradd --create-home --uid 1000 arya && mkdir /data && chown arya /data
USER arya

ENV ARYA_MODE=practice \
    ARYA_SEED=1 \
    ARYA_DB_PATH=/data/arya_payments.db \
    PYTHONUNBUFFERED=1

# Mount /data to look at (or keep) the SQLite database: -v "$PWD/data:/data"
VOLUME ["/data"]
EXPOSE 8000 4173

HEALTHCHECK --interval=10s --timeout=3s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request as u; u.urlopen('http://127.0.0.1:8000/health', timeout=2); u.urlopen('http://127.0.0.1:4173/api/health', timeout=2)"

CMD ["python", "run_sandbox.py"]
