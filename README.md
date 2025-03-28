"""
# Geoflip Open

**Geoflip Open** is the open-source backend of [Geoflip](https://geoflip.io) — a modern, self-hostable spatial API for transforming geospatial files like **Shapefile**, **DXF**, **GeoJSON**, and **GeoPackage**.

It supports transformations such as buffering, clipping, appending, and CRS conversion — all accessible via a simple HTTP API. Built with Flask, Celery, and designed for developers who want geoprocessing power without requiring enterprise tools.

📚 View the API documentation: [docs.geoflip.io](https://docs.geoflip.io)
Check out the YouTube channel: [video tutorials](https://youtube.com/@geoflip)

---

## ✨ Features

- Upload and transform spatial files via API
- Supports GeoJSON, SHP, GPKG, and DXF formats
- Handles buffering, clipping, merging, appending, reprojection, and more
- Asynchronous processing powered by Celery + Redis
- Stateless — no auth, no billing

---

## 🚀 Quick Start with Docker

Spin up the full backend stack locally.

### 1. Clone the repo
```bash
git clone https://github.com/yourusername/geoflip-open.git
cd geoflip-open
```

### 2. Copy the example env file

```bash
cp .env.example .env
```

### 3. Start it up
```bash
docker-compose up --build -d
```

### 5. Test it!
Use Postman, Insomnia, curl, or your frontend app  
- The base url will be `http://localhost:8000/` if you use the example env
- Then just review the Docs: [https://docs.geoflip.io](https://docs.geoflip.io)
- You can also import the postman collection
    - look for `GeoFlip Open.postman_collection.json` in the root of the project
- example payload to: `http://localhost:8000/v1/transform/geojson`

```json
{
  "input_geojson":{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "properties": {"id": 1, "group": "A"},
      "geometry": {
        "type": "Polygon",
        "coordinates": [
          [
            [-73.981, 40.768],
            [-73.981, 40.769],
            [-73.982, 40.769],
            [-73.982, 40.768],
            [-73.981, 40.768]
          ]
        ]
      }
    },
    {
      "type": "Feature",
      "properties": {"id": 2, "group": "A"},
      "geometry": {
        "type": "Polygon",
        "coordinates": [
          [
            [-73.983, 40.768],
            [-73.983, 40.769],
            [-73.984, 40.769],
            [-73.984, 40.768],
            [-73.983, 40.768]
          ]
        ]
      }
    },
    {
      "type": "Feature",
      "properties": {"id": 3, "group": "B"},
      "geometry": {
        "type": "Polygon",
        "coordinates": [
          [
            [-73.985, 40.768],
            [-73.985, 40.769],
            [-73.986, 40.769],
            [-73.986, 40.768],
            [-73.985, 40.768]
          ]
        ]
      }
    }
  ]
    },
  "output_format": "geojson",
  "output_crs": "EPSG:4326",
  "transformations":[
    {
        "type":"buffer",
        "distance": 100,
        "units": "meters"
    },
    {
        "type":"union"
    }
  ]
}
```

---

## 🧑‍💻 Run in Local Dev Mode (No Docker)

This is more involved but if you are editing the code this is what you want to do.

### 1. Clone and set up your environment
```bash
git clone https://github.com/intelligis-io/geoflip-open
cd geoflip-open
cp .env.example .env
# Modify it with the below - or something similar
# API_URL=http://localhost:5000
# UPLOADS_PATH=./uploads
# OUTPUT_PATH=./output
```

### 2. setup a virtual environment (make sure you are using python 3.11+)
```bash
python -m venv .venv
```
and activate it in your environment (ie set it as your python environment)

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Start Celery (in a separate terminal)
```bash
celery -A make_celery.celery_app worker --pool=solo --loglevel=INFO
```

### 4. Run the Flask app
```bash
flask run
```

Or if you want to use Gunicorn:

```bash
gunicorn --workers 3 --bind 0.0.0.0:8000 'app:create_app()'
```

---

## 🤔 Need More?

Looking for authentication, usage tracking, billing, or enhanced enterprise features?  
Head to [geoflip.io](https://geoflip.io) to try the full hosted version.

or checkout our youtube for [video tutorials](https://youtube.com/@geoflip)

---

## 📄 License

BSL — free to use, fork, and extend.
"""
