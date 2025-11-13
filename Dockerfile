FROM ghcr.io/osgeo/gdal:ubuntu-small-3.12.0

# Install system dependencies required by rasterio & rio-stac
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-pip python3-setuptools build-essential python3-dev git build-essential

RUN apt-get autoremove -y && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Set working directory
WORKDIR /app

COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt --break-system-packages

# Copy scripts
COPY . .

# Default command
ENTRYPOINT ["python", "ingest_stac.py"]
