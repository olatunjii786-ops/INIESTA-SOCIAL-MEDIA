FROM python:3.11-slim

# Install ffmpeg
RUN apt-get update && apt-get install -y ffmpeg \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Copy files
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install -U yt-dlp

COPY . .

# Render uses PORT env
ENV PORT=10000

# Start server
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:10000", "--workers", "2", "--threads", "4"]
