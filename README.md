# EOxHub Helpers

This repository contains a collection of helper scripts and utilities for processing and managing geospatial data within the EOxHub ecosystem.

## Available Tools

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

