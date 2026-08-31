import os
import glob
import math
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import rasterio
from rasterio.warp import transform_bounds
from rasterio.crs import CRS
import numpy as np

app = FastAPI()

# Directory inside container where FABDEM tiles live
TILE_DIR = "/data/fabdem"

# In-memory list of opened datasets
tile_datasets = []

class Point(BaseModel):
    lat: float
    lon: float

class BatchRequest(BaseModel):
    points: List[Point]

class BatchResponse(BaseModel):
    elevations: List[Optional[float]]

def load_tiles():
    global tile_datasets
    tile_paths = glob.glob(os.path.join(TILE_DIR, "*.tif"))
    if not tile_paths:
        raise RuntimeError(f"No .tif files found in {TILE_DIR}")
    for path in tile_paths:
        ds = rasterio.open(path)
        tile_datasets.append(ds)

def get_elevation(lat: float, lon: float) -> Optional[float]:
    for ds in tile_datasets:
        # Check if point is within this tile's bounds
        min_lon, min_lat, max_lon, max_lat = ds.bounds
        if (min_lon <= lon <= max_lon) and (min_lat <= lat <= max_lat):
            # Convert lat/lon to pixel coordinates
            row, col = ds.index(lon, lat)
            if 0 <= row < ds.height and 0 <= col < ds.width:
                val = ds.read(1, window=((row, row+1), (col, col+1)))
                if val.size > 0:
                    elevation = float(val[0, 0])
                    # FABDEM uses -9999 or similar for NoData; check nodata value
                    nodata = ds.nodata
                    if nodata is not None and math.isclose(elevation, nodata, rel_tol=0, abs_tol=1e-6):
                        return None
                    return elevation
    # Outside all tiles
    return None

@app.on_event("startup")
def startup_event():
    load_tiles()

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/elev/batch", response_model=BatchResponse)
def elev_batch(req: BatchRequest):
    elevations = []
    for p in req.points:
        elev = get_elevation(p.lat, p.lon)
        elevations.append(elev)
    return BatchResponse(elevations=elevations)

@app.get("/elev")
def elev_single(lat: float, lon: float):
    elev = get_elevation(lat, lon)
    return {"lat": lat, "lon": lon, "elevation": elev}