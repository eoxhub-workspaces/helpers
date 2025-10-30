import os
import re
import argparse
import rasterio
import numpy as np
import geopandas as gpd
import pandas as pd
from rasterio.mask import mask
from datetime import datetime
from shapely.ops import unary_union

import logging

# At the top of your script
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def parse_args():
    parser = argparse.ArgumentParser(description="Compute zonal statistics from COGs per region")
    parser.add_argument("-t", "--tiffs", nargs="+", required=True, help="Single or multiple COG TIFFs")
    parser.add_argument("-g", "--geometry", required=True, help="Geometry file (GeoJSON or Shapefile)")
    parser.add_argument("-b", "--band-names", nargs="+", help="Optional names for each band")
    parser.add_argument("-o", "--output", required=True, help="Output GeoJSON file")
    parser.add_argument("--export-csv", action="store_true", help="Export timeseries per feature as CSV files")
    parser.add_argument("--csv-dir", default="timeseries_csv", help="Directory to save CSV files if --export-csv is used")
    parser.add_argument("--id-field", default="id", help="Field name to use as unique feature ID (fallback: index)")
    parser.add_argument("--simplify", type=float, help="Simplify output geometries by this tolerance (in CRS units)")
    parser.add_argument("--preserve-topology", action="store_true", help="Preserve topology between touching features")
    return parser.parse_args()

def extract_date_from_filename(filename):
    # Extract date in YYYYMMDD or YYYY-MM-DD formats
    match = re.search(r'(\d{4}[-_]?\d{2}[-_]?\d{2})', filename)
    if match:
        date_str = re.sub(r'[-_]', '', match.group(1))
        return datetime.strptime(date_str, "%Y%m%d")
    return None

def compute_statistics(raster_path, shapes, band_names=None):
    """
    Compute per-geometry statistics (min, max, mean, std, pixel counts) for each band.
    """
    logging.info(f"Opening raster: {raster_path}")
    stats_list = []

    with rasterio.open(raster_path) as src:
        nodata = src.nodata
        logging.debug(f"Raster bands: {src.count}, nodata: {nodata}")

        for i, band in enumerate(src.indexes):
            band_name = band_names[i] if band_names and i < len(band_names) else f"band_{band}"
            band_stats = []

            logging.info(f"Processing {band_name} ...")

            for geom_idx, geom in enumerate(shapes.geometry):
                try:
                    out_image, _ = mask(src, [geom], crop=True)
                except Exception as e:
                    logging.warning(f"Failed to mask geometry {geom_idx}: {e}")
                    band_stats.append({
                        f"{band_name}_min": None,
                        f"{band_name}_max": None,
                        f"{band_name}_mean": None,
                        f"{band_name}_std": None,
                        f"{band_name}_count": 0,
                        f"{band_name}_valid": 0,
                        f"{band_name}_invalid": 0
                    })
                    continue

                data = out_image[band - 1]
                total_pixels = data.size

                if nodata is not None:
                    valid_mask = data != nodata
                else:
                    valid_mask = np.isfinite(data)

                valid_pixels = np.count_nonzero(valid_mask)
                invalid_pixels = total_pixels - valid_pixels
                valid_data = data[valid_mask]

                if valid_pixels == 0:
                    band_stats.append({
                        f"{band_name}_min": None,
                        f"{band_name}_max": None,
                        f"{band_name}_mean": None,
                        f"{band_name}_std": None,
                        f"{band_name}_count": int(total_pixels),
                        f"{band_name}_valid": 0,
                        f"{band_name}_invalid": int(invalid_pixels)
                    })
                else:
                    band_stats.append({
                        f"{band_name}_min": float(np.min(valid_data)),
                        f"{band_name}_max": float(np.max(valid_data)),
                        f"{band_name}_mean": float(np.mean(valid_data)),
                        f"{band_name}_std": float(np.std(valid_data)),
                        f"{band_name}_count": int(total_pixels),
                        f"{band_name}_valid": int(valid_pixels),
                        f"{band_name}_invalid": int(invalid_pixels)
                    })

                if geom_idx % 10 == 0:
                    logging.debug(f"Processed geometry {geom_idx+1}/{len(shapes)} for {band_name}")

            stats_list.append(band_stats)

    # Merge stats per geometry
    combined_stats = []
    for i in range(len(shapes)):
        geom_stats = {}
        for band_stats in stats_list:
            geom_stats.update(band_stats[i])
        combined_stats.append(geom_stats)

    return combined_stats

def main():
    args = parse_args()
    gdf = gpd.read_file(args.geometry)

    logging.info(f"Loaded {len(gdf)} features from {args.geometry}")

    # Simplify upfront to speed up raster masking
    if args.simplify and args.simplify > 0:
        logging.info(f"Simplifying geometries before computation (tolerance={args.simplify}, preserve_topology={args.preserve_topology})")
        if args.preserve_topology:
            gdf.geometry = gdf.geometry.simplify(args.simplify, preserve_topology=True)
        else:
            gdf.geometry = gdf.geometry.simplify(args.simplify, preserve_topology=False)
        logging.info("Simplification complete.")

    logging.info(f"Processing {len(args.tiffs)} TIFF(s)")

    # Create CSV directory if exporting timeseries
    if args.export_csv:
        os.makedirs(args.csv_dir, exist_ok=True)

    if len(args.tiffs) == 1:
        stats = compute_statistics(args.tiffs[0], gdf, args.band_names)
        # Ensure the column exists before assignment
        if 'statistics' not in gdf.columns:
            gdf['statistics'] = [None] * len(gdf)

        for i, stat in enumerate(stats):
            gdf.at[i, 'statistics'] = stat
    else:
        # Initialize timeseries column as a list for all rows
        if 'timeseries' not in gdf.columns:
            gdf['timeseries'] = [[] for _ in range(len(gdf))]
        else:
            # Convert any dict entries to a list of objects
            def convert_ts(value):
                if isinstance(value, dict):
                    return [{"date": k, **v} for k, v in value.items()]
                elif isinstance(value, list):
                    return value
                else:
                    return []
            gdf['timeseries'] = gdf['timeseries'].apply(convert_ts)

        for tiff_idx, tiff in enumerate(args.tiffs, start=1):
            logging.info(f"[{tiff_idx}/{len(args.tiffs)}] Processing TIFF: {tiff}")
            date = extract_date_from_filename(os.path.basename(tiff))
            date_key = date.strftime("%Y-%m-%d") if date else os.path.basename(tiff)
            stats = compute_statistics(tiff, gdf, args.band_names)

            logging.info(f"Computed statistics for {len(stats)} features in {tiff}")

            for i, stat in enumerate(stats):
                if i % 10 == 0:  # Log every 10 features to avoid spamming
                    logging.debug(f"Processing feature {i+1}/{len(stats)}")
                ts_list = gdf.at[i, 'timeseries']
                entry = {"date": date_key}
                entry.update(stat)
                ts_list.append(entry)
                gdf.at[i, 'timeseries'] = ts_list

        # Optionally export to CSV
        if args.export_csv:
            logging.info(f"Exporting timeseries CSVs to {args.csv_dir}")
            for i, row in gdf.iterrows():
                fid = str(row[args.id_field]) if args.id_field in gdf.columns else f"feature_{i}"
                ts_data = row.get("timeseries", [])
                if not ts_data:
                    continue

                # Convert list of dicts to DataFrame
                df = pd.DataFrame(ts_data)

                # Sort by date if needed
                if "date" in df.columns:
                    df["date"] = pd.to_datetime(df["date"])
                    df = df.sort_values("date")

                csv_path = os.path.join(args.csv_dir, f"{fid}.csv")
                df.to_csv(csv_path, index=False)
                logging.debug(f"Saved CSV for feature {fid}")

    if 'timeseries' in gdf.columns and args.export_csv:
        gdf = gdf.drop(columns=['timeseries'])
    # Save GeoJSON
    gdf.to_file(args.output, driver="GeoJSON")
    print(f"\nGeoJSON saved to {args.output}")

if __name__ == "__main__":
    main()
