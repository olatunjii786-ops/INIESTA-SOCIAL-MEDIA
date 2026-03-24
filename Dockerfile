# Use a lightweight Python image
FROM python:3.11-slim

# Install system dependencies (ffmpeg is needed for some sites)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the code
COPY . .

# Run the app with Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:10000", "app:app"]
