FROM postgres:18

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
    postgresql-server-dev-18 \
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

# Copy initialization SQL scripts into the image so they run on first init
COPY initdb /docker-entrypoint-initdb.d/
RUN chmod -R 755 /docker-entrypoint-initdb.d

# Keep the default entrypoint from postgres image
