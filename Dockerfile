FROM node:22-bookworm-slim AS node-runtime
FROM python:3.12-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    HF_HOME=/opt/huggingface \
    HF_HUB_DISABLE_TELEMETRY=1 \
    OMP_NUM_THREADS=2 \
    TOKENIZERS_PARALLELISM=false \
    PORT=8080

COPY --from=node-runtime /usr/local/bin/node /usr/local/bin/node
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 10001 careweave
WORKDIR /app
COPY requirements.txt ./
# CPU wheels avoid downloading CUDA libraries into this CPU-only service.
RUN pip install torch==2.15.0 --index-url https://download.pytorch.org/whl/cpu \
    && pip install -r requirements.txt
COPY rag/ ./rag/
COPY data/ ./data/
COPY src/ ./src/
COPY scripts/plan-stdio.mjs ./scripts/plan-stdio.mjs
COPY .streamlit/config.toml ./.streamlit/config.toml
COPY streamlit_app.py ./
COPY deploy/ ./deploy/
# Download the pinned public model during the build, not during a visitor's request.
RUN python -m deploy.cache_model \
    && mkdir -p /app/.careweave \
    && chown -R careweave:careweave /app/.careweave /opt/huggingface
USER careweave
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD python -c "import os,urllib.request; urllib.request.urlopen('http://127.0.0.1:'+os.environ.get('PORT','8080')+'/_stcore/health',timeout=4)"
CMD ["python", "deploy/start.py"]
