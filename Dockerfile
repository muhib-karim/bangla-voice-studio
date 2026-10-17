# syntax=docker/dockerfile:1
ARG PYTHON_IMAGE=python:3.11-slim-bookworm
FROM ${PYTHON_IMAGE} AS builder
ENV PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
WORKDIR /build
COPY pyproject.toml README.md LICENSE THIRD_PARTY_NOTICES.md ./
COPY src ./src
RUN python -m pip install 'torch>=2.4,<3' --index-url https://download.pytorch.org/whl/cpu \
    && python -m pip install '.[mms,asr]'

FROM ${PYTHON_IMAGE} AS runtime
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 10001 bvs \
    && useradd --uid 10001 --gid 10001 --create-home bvs \
    && mkdir /models /data \
    && chown bvs:bvs /models /data
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    BVS_MODEL_CACHE=/models BVS_DATA_DIR=/data \
    HF_HOME=/models/hf HF_HUB_CACHE=/models/hf/hub \
    BVS_OFFLINE=1 HF_HUB_OFFLINE=1 \
    OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=1
USER 10001:10001
WORKDIR /data
VOLUME ["/models", "/data"]
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3).close()"
ENTRYPOINT ["bvs"]
CMD ["serve", "--host", "0.0.0.0", "--port", "8000"]
