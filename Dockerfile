# Use a lightweight Python image
FROM python:3.10-slim

# Install system dependencies (FFmpeg is the most important)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory
WORKDIR /app

# Copy requirements and install them
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your app code
COPY . .

# Start the FastAPI server using Uvicorn
# Render uses the $PORT environment variable automatically
CMD uvicorn main:app --host 0.0.0.0 --port $PORT
