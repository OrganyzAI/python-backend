FROM postgres:17

ENV PGVECTOR_VERSION=

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
    ca-certificates \
    build-essential \
    git \
    gcc \
    make \
    wget \
    libssl-dev \
    postgresql-server-dev-17 \
    && rm -rf /var/lib/apt/lists/*

RUN if [ -z "${PGVECTOR_VERSION}" ]; then \
    git clone --depth 1 https://github.com/pgvector/pgvector.git /tmp/pgvector; \
    else \
    git clone --depth 1 --branch ${PGVECTOR_VERSION} https://github.com/pgvector/pgvector.git /tmp/pgvector; \
    fi \
    && cd /tmp/pgvector \
    && make \
    && make install \
    && cd / \
    && rm -rf /tmp/pgvector


COPY --chown=postgres:postgres initdb /docker-entrypoint-initdb.d/
RUN find /docker-entrypoint-initdb.d -type d -exec chmod 555 {} \; \
    && find /docker-entrypoint-initdb.d -type f -exec chmod 444 {} \;

USER postgres
