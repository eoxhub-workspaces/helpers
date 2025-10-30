# EOxHub Helpers

This repository contains a collection of helper scripts and utilities for processing and managing geospatial data within the EOxHub ecosystem.

## Available Tools
- resample: allows exactly fitting one cloud optimized geotiff to the extent of another reference datasets
- zonal_stats: allows pre-calculating zonal statistics of raster data based on supplied geometries


## Environment
A requirements.txt has been made available that covers the dependencies of all scripts, if you want to make sure they can run you can use for example conda to set it up:
```bash
conda create -n helpers python=3.11
conda activate helpers
conda install -c conda-forge gdal # make sure gdal is available in environment
pip install -r requirements.txt
```
---

### resample.py

A Python script for resampling geospatial raster data to match a reference dataset's properties.

#### Features
- Reprojects and resamples source data to match reference data
- Preserves original data values using nearest neighbor resampling
- Automatically builds overviews (pyramids) for efficient visualization
- Uses LZW compression and tiling for optimized storage and access
- Supports BigTIFF format for large datasets

#### Requirements
- GDAL Python bindings (osgeo)
- Input rasters must be readable by GDAL

#### Usage
```bash
python resample.py <source_file> <reference_file>
```

---

### zonal_stats

#### Usage

Python script to extract pixel statistics of a single or timeseries of tiffs
based on passed geometries, such as administrative zones.

**Single TIFF**

```bash
python zonal_stats.py -t my_cog.tif -g polygons.geojson -o output.geojson
```

**Multiple TIFFs (time series)**

```bash
python zonal_stats.py -t data/*.tif -g polygons.shp -o output.geojson
```

**Time series + export to CSV**

```bash
python zonal_stats.py -t data/*.tif -g polygons.geojson -o output.geojson --export-csv --id-field id
```

This will:

* Save a GeoJSON with aggregated per-feature stats.
* Create a `timeseries_csv/` directory with one CSV per feature (named by `region_id`).
* Each CSV will have one row per date (extracted from TIFF filenames).

**Simplification**
If your input geometry is large / complex, it is possible to directly apply simplification by adding following flags
```bash
--simplify 50 --preserve-topology
```


