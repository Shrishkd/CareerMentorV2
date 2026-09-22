FROM python:3.11-slim

# ffmpeg decodes browser audio for Whisper; libgl/libglib are needed by OpenCV/MediaPipe.
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg libgl1 libglib2.0-0 && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

# The LLM runs in Ollama; point OLLAMA_HOST at it (e.g. http://host.docker.internal:11434).
ENV OLLAMA_HOST=http://host.docker.internal:11434 \
    LLM_MODEL=qwen3:4b \
    WHISPER_MODEL=base

EXPOSE 8000
# One worker: the grading queue and monitoring state live in-process.
CMD ["gunicorn", "backend_api:app", "-w", "1", "--threads", "8", "-b", "0.0.0.0:8000", "--timeout", "600"]
