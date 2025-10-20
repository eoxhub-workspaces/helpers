#!/usr/bin/env python3
"""
Resample Geospatial Raster Data

This script resamples a source raster to match the spatial reference, resolution, and extent
of a reference raster using GDAL (Geospatial Data Abstraction Library).

Features:
- Reprojects and resamples source data to match reference data
- Preserves original data values using nearest neighbor resampling
- Automatically builds overviews (pyramids) for efficient visualization
- Uses LZW compression and tiling for optimized storage and access
- Supports BigTIFF format for large datasets

Requirements:
- GDAL Python bindings (osgeo)
- Input rasters must be readable by GDAL

Usage:
    python resample.py <source_file> <reference_file>

Arguments:
    source_file    : Path to the input raster that needs to be resampled
    reference_file : Path to the reference raster whose properties should be matched

Output:
    The script creates two new files:
    1. source_file_matched.tif     : Resampled version of the source file
    2. reference_file_matched.tif  : Copy of reference file in float32 format

Example:
    python resample.py input.tif reference.tif

Note:
    Both output files will be created in the same directory as their respective
    input files with '_matched' appended to the filename.
"""

import sys
import os
from osgeo import gdal, gdalconst

def print_overview_sizes(ds, label):
    band = ds.GetRasterBand(1)
    print(f"{label} base size: {band.XSize}x{band.YSize}")
    for i in range(band.GetOverviewCount()):
        ov = band.GetOverview(i)
        print(f"  Overview {i}: {ov.XSize}x{ov.YSize}")

def build_and_print_overviews(filename, label):
    """
    Build overview pyramids for a raster dataset and print their dimensions.
    
    Creates overview pyramids (reduced resolution versions) of the dataset
    using powers of 2 until the smallest dimension is less than 64 pixels.
    Uses nearest neighbor resampling to preserve original values.
    
    Args:
        filename (str): Path to the raster file
        label (str): Label to identify the dataset in the output
    """
    ds = gdal.Open(filename, gdalconst.GA_Update)
    base_band = ds.GetRasterBand(1)
    min_dim = min(base_band.XSize, base_band.YSize)
    factors = []
    f = 2
    while min_dim // f > 64:
        factors.append(f)
        f *= 2
    if factors:
        ds.BuildOverviews('NEAREST', factors)
    print_overview_sizes(ds, label)
    ds = None

if len(sys.argv) != 3:
    print(f"Usage: {sys.argv[0]} <source_file> <reference_file>")
    sys.exit(1)

src_filename = os.path.abspath(sys.argv[1])
ref_filename = os.path.abspath(sys.argv[2])

def matched_name(filename):
    base, ext = os.path.splitext(filename)
    return f"{base}_matched{ext}"

dst_filename = matched_name(src_filename)
aligned_ref_filename = matched_name(ref_filename)

src = gdal.Open(src_filename, gdalconst.GA_ReadOnly)
ref = gdal.Open(ref_filename, gdalconst.GA_ReadOnly)

ref_proj = ref.GetProjection()
ref_geotrans = ref.GetGeoTransform()
ref_width = ref.RasterXSize
ref_height = ref.RasterYSize
src_proj = src.GetProjection()

driver = gdal.GetDriverByName('GTiff')
# Create aligned reference raster
aligned_ref = driver.Create(aligned_ref_filename, ref_width, ref_height, ref.RasterCount, gdalconst.GDT_Float32,
                    options=['TILED=YES','COMPRESS=LZW','BIGTIFF=IF_SAFER','COPY_SRC_OVERVIEWS=YES'])
aligned_ref.SetGeoTransform(ref_geotrans)
aligned_ref.SetProjection(ref_proj)
gdal.ReprojectImage(ref, aligned_ref, ref_proj, ref_proj, gdalconst.GRA_NearestNeighbour)
del aligned_ref

# Create output raster (aligned to reference)
dst = driver.Create(dst_filename, ref_width, ref_height, src.RasterCount, gdalconst.GDT_Float32,
                    options=['TILED=YES','COMPRESS=LZW','BIGTIFF=IF_SAFER','COPY_SRC_OVERVIEWS=YES'])
dst.SetGeoTransform(ref_geotrans)
dst.SetProjection(ref_proj)
gdal.ReprojectImage(src, dst, src_proj, ref_proj, gdalconst.GRA_NearestNeighbour)
del dst

# Build overviews for both aligned rasters
build_and_print_overviews(aligned_ref_filename, "Aligned Reference")
build_and_print_overviews(dst_filename, "Output")
