# Voice Cleaner container. Works on Hugging Face Spaces, Render, Railway, Fly.io, Cloud Run, etc.
#   docker build -t voice-cleaner .
#   docker run -p 7860:7860 voice-cleaner
FROM python:3.11-slim

# git: DeepFilterNet calls it at startup and crashes if it's missing.
RUN apt-get update && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

# Hugging Face Spaces runs containers as user 1000.
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    MAX_UPLOAD_MB=100
WORKDIR /home/user/app

# CPU-only PyTorch first (the default Linux build pulls in ~2 GB of GPU libraries).
RUN pip install --no-cache-dir --user \
    torch==2.0.1 torchaudio==2.0.2 --index-url https://download.pytorch.org/whl/cpu

COPY --chown=user requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

COPY --chown=user . .

EXPOSE 7860
CMD ["sh", "-c", "uvicorn app:app --host 0.0.0.0 --port ${PORT:-7860}"]
