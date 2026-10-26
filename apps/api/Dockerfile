FROM node:24.22.0-slim AS web-build

WORKDIR /workspace

COPY package.json package-lock.json ./
RUN npm ci

COPY apps/web ./apps/web
COPY contracts/generated ./contracts/generated
ARG VITE_LISTINGS_PUBLIC_DEMO=false
ARG VITE_MICROSOFT_SIGN_IN_ENABLED=false
ENV VITE_LISTINGS_PUBLIC_DEMO=${VITE_LISTINGS_PUBLIC_DEMO} \
    VITE_MICROSOFT_SIGN_IN_ENABLED=${VITE_MICROSOFT_SIGN_IN_ENABLED}
RUN npm run build

FROM python:3.14.8-slim-trixie AS build

COPY --from=ghcr.io/astral-sh/uv:0.10.7 /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --no-install-project

FROM python:3.14.8-slim-trixie AS runtime

# psycopg's bundled OpenSSL defaults to a wheel-build path. Point both clients at
# the installed OS roots while keeping sslrootcert=system and verify-full intact.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH=/opt/venv/bin:$PATH \
    CLIP_ENVIRONMENT=production \
    CLIP_DEBUG=false \
    SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt

WORKDIR /app

# Vendor only the reviewed regional RDS roots; keep normal system roots and full
# hostname verification. No certificate download occurs during image build.
COPY apps/api/app/domains/identity/certificates/*.crt /usr/local/share/ca-certificates/clip-rds/
RUN update-ca-certificates

COPY --from=build --chown=10001:10001 /opt/venv /opt/venv
COPY --chown=10001:10001 apps/api/app /app/apps/api/app
COPY --from=web-build --chown=10001:10001 /workspace/apps/web/dist /app/web

USER 10001:10001

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD ["python", "-c", "import json, urllib.request; assert json.load(urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2)) == {'status': 'ok'}"]

CMD ["uvicorn", "app.main:app", "--app-dir", "apps/api", "--host", "0.0.0.0", "--port", "8000"]
