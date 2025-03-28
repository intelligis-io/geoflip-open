FROM python:3.12

# Set working directory
WORKDIR /app

# Install system dependencies required for GDAL and NumPy
RUN apt-get update && apt-get install -y \
    gdal-bin \
    libgdal-dev \
    python3-dev \
    build-essential \
    && apt-get clean

# Set environment variables to help find gdal-config
ENV CPLUS_INCLUDE_PATH=/usr/include/gdal
ENV C_INCLUDE_PATH=/usr/include/gdal

# Install pip and NumPy before installing GDAL
RUN pip install --no-cache-dir --upgrade pip setuptools wheel
RUN pip install --no-cache-dir numpy

# Install GDAL
RUN pip install --no-cache-dir GDAL==$(gdal-config --version | awk -F'[.]' '{print $1"."$2"."$3}')

# Copy the requirements.txt file
COPY requirements.txt .

# Install Python dependencies (including Fiona)
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Start the application (Celery + Gunicorn)
CMD /bin/bash -c "celery -A make_celery.celery_app worker --concurrency=4 --loglevel INFO & gunicorn --workers 3 --timeout 200 --worker-class gevent --bind 0.0.0.0:8000 'app:create_app()'"