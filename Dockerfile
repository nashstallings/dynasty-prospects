# Cloud Run image. Small on purpose: the running service is just a static
# page plus a pre-baked JSON file -- it never talks to CFBD or BigQuery -- and
# every megabyte here is cold-start latency you pay for on a service that
# scales to zero.
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Dependencies first, so a change to the app does not re-resolve the wheel set.
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
# nfl_data_py pins pandas<2.0/numpy<2.0, which would drag the resolver above
# back down to a pandas with no Python 3.11 wheel if installed in the same
# step -- see requirements.txt and notebooks/colab_runner.ipynb for the same
# fix applied there. Keep this a separate, --no-deps step.
RUN pip install --no-cache-dir --no-deps nfl_data_py==0.3.3

COPY pyproject.toml ./
COPY src/ ./src/
RUN pip install --no-cache-dir --no-deps -e .

COPY web/ ./web/
COPY data/ ./data/

# Cloud Run sends traffic to $PORT and expects the container to listen on
# every interface. The loopback default that protects a laptop would refuse
# it.
ENV HOST=0.0.0.0 \
    PORT=8080
EXPOSE 8080

# Run as a non-root user; nothing here needs to write to the filesystem --
# this service only ever reads the pre-baked dashboard.json.
RUN useradd --create-home --uid 1000 app && chown -R app:app /app
USER app

CMD exec uvicorn dynasty_prospects.server:app --host 0.0.0.0 --port ${PORT} --log-level warning
