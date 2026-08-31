FROM python:3.11-slim

WORKDIR /app

# Install system dependencies needed for rasterio
RUN apt-get update && apt-get install -y \
    gdal-bin \
    libgdal-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY main.py .

# Create directory for FABDEM tiles
RUN mkdir -p /data/fabdem

# Copy tiles into the image
COPY fabdem-tiles/ /data/fabdem/

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]