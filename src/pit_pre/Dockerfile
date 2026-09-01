ARG DOCKERHUB_PREFIX=
ARG PYTORCH_CPU_INDEX_URL=https://download.pytorch.org/whl/cpu

FROM ${DOCKERHUB_PREFIX}python:3.10.19-slim-bookworm AS dependencies
ARG PYTORCH_CPU_INDEX_URL
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /app
COPY requirements.lock.txt requirements-mysql-auth.lock.txt ./
RUN --mount=type=cache,target=/root/.cache/pip \
    python -m pip install --upgrade pip \
    && python -m pip install --index-url "${PYTORCH_CPU_INDEX_URL}" --extra-index-url https://pypi.org/simple torch==2.11.0+cpu \
    && python -m pip install -r requirements.lock.txt -r requirements-mysql-auth.lock.txt

FROM dependencies AS test
COPY . ./
RUN python -m unittest discover -s tests -p 'test_*.py' -v \
    && python -m compileall -q pit_pre tests

FROM test AS runtime
RUN chmod 0555 /app/docker-entrypoint.sh \
    && useradd --create-home --uid 10001 --shell /usr/sbin/nologin pitpre \
    && chown -R pitpre:pitpre /app
USER pitpre
ENTRYPOINT ["/app/docker-entrypoint.sh"]
