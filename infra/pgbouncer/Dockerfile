FROM python:3.14.8-slim-trixie

# Debian's security-maintained build, fixed for the experiment. No cloud SDK or
# application code is needed: ECS injects only the three original DSNs and TLS.
RUN apt-get update && apt-get install -y --no-install-recommends pgbouncer=1.24.1-1+deb13u2 \
    && rm -rf /var/lib/apt/lists/*
COPY apps/api/app/domains/identity/certificates/*.crt /usr/local/share/ca-certificates/clip-rds/
RUN update-ca-certificates
COPY infra/pgbouncer/requirements.txt /opt/clip-pool/requirements.txt
RUN pip install --no-cache-dir --require-hashes -r /opt/clip-pool/requirements.txt
COPY infra/pgbouncer/entrypoint.py /opt/clip-pool/entrypoint.py
ENV SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt PYTHONUNBUFFERED=1
USER 10001:10001
EXPOSE 6432
ENTRYPOINT ["python", "/opt/clip-pool/entrypoint.py"]
