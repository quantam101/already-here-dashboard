# D-ASI v4.0.0-ENTERPRISE — HF Spaces container
# Runtime: Python 3.11-slim, port 7860, UID 1000 (kernel_worker)
# Workers: 1 — mandatory for single-process asyncio job state isolation.

FROM python:3.11-slim

# HF Spaces requires UID 1000 (kernel_worker)
RUN useradd -m -u 1000 kernel_worker

WORKDIR /app

# Install dependencies as root, then hand off to kernel_worker
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY main.py .
COPY agent_manifest.yaml .

# Job output directory — owned by kernel_worker
RUN mkdir -p /app/data/dasi_jobs && chown -R kernel_worker:kernel_worker /app

USER kernel_worker

# HF Spaces mandatory port
EXPOSE 7860

# Single worker — critical for asyncio job isolation and background tasks
CMD ["uvicorn", "main:app", \
     "--host", "0.0.0.0", \
     "--port", "7860", \
     "--workers", "1", \
     "--log-level", "info"]
