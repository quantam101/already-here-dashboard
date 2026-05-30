FROM python:3.11-slim

# Set strict production environmental variable bindings
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    HOME=/home/kernel_worker \
    PATH=/home/kernel_worker/.local/bin:$PATH

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Strict compliance with Hugging Face Space UID user isolation expectations
RUN useradd -m -u 1000 kernel_worker
USER kernel_worker
WORKDIR $HOME/app

# Process software requirements layer
COPY --chown=kernel_worker:kernel_worker requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Bind structural code definitions
COPY --chown=kernel_worker:kernel_worker . .

EXPOSE 7860

# Execute optimized asynchronous multi-process runtime engine
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860", "--workers", "4", "--timeout-keep-alive", "120", "--log-level", "warning"]
