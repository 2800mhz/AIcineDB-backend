FROM python:3.11-slim

WORKDIR /app

# System dependencies for opencv, audio processing, and other requirements
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libsndfile1 \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Expose port (Railway will override with $PORT)
EXPOSE 8000

# Start command
CMD uvicorn backend.api.main:app --host 0.0.0.0 --port ${PORT:-8000}
