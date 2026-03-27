FROM python:3.11-slim

# Install ffmpeg for audio conversion (OGG -> WAV)
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies (no whisper — using API-based transcription)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ src/
COPY run_bot.py .

# Data volume for SQLite database
VOLUME /app/data

CMD ["python", "run_bot.py"]
