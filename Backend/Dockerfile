# Use official slim Python image
FROM python:3.11-slim

# Install system dependencies (ffmpeg, libgl1, portaudio for sounddevice)
RUN apt-get update && \
    apt-get install -y ffmpeg libgl1 libportaudio2 portaudio19-dev && \
    rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first
COPY requirements.txt .

# Install Python deps
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY . .

# Expose port
EXPOSE 8000

# Start app with gunicorn
CMD ["gunicorn", "backend_api:app", "-w", "2", "-k", "gthread", "-b", "0.0.0.0:8000", "--timeout", "120"]
