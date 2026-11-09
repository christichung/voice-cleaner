# Hugging Face Space build: pulls the app from GitHub and builds it with the repo's own Dockerfile steps.
# Hugging Face rejects binary files (the model weights) pushed without Git LFS, so instead of
# copying the app into the Space, this clones it from GitHub at build time.
FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    MAX_UPLOAD_MB=100
WORKDIR /home/user

RUN pip install --no-cache-dir --user \
    torch==2.0.1 torchaudio==2.0.2 --index-url https://download.pytorch.org/whl/cpu

# This file changes whenever main gets a new commit, so a rebuild picks up the latest code.
ADD https://api.github.com/repos/christichung/voice-cleaner/git/refs/heads/main /tmp/latest-commit.json
RUN git clone --depth 1 https://github.com/christichung/voice-cleaner.git app
WORKDIR /home/user/app
RUN pip install --no-cache-dir --user -r requirements.txt

EXPOSE 7860
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "7860"]
