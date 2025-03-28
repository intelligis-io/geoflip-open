import pandas as pd
import geopandas as gpd

def merge_geodataframes(gdfs):
    """
    Merges a list of GeoDataFrames into a single GeoDataFrame, ensuring all have the same CRS.

    Parameters:
    gdfs (list of gpd.GeoDataFrame): List of GeoDataFrames to merge.

    Returns:
    gpd.GeoDataFrame: A single merged GeoDataFrame.
    """
    if not gdfs:
        return None

    # Check if all GeoDataFrames have the same CRS
    crs_list = [gdf.crs for gdf in gdfs]
    if len(set(crs_list)) > 1:
        # If CRS are different, transform all to the CRS of the first GeoDataFrame
        target_crs = gdfs[0].crs
        transformed_gdfs = []
        for gdf in gdfs:
            if gdf.crs != target_crs:
                transformed_gdfs.append(gdf.to_crs(target_crs))
            else:
                transformed_gdfs.append(gdf)
        gdfs = transformed_gdfs

    # Merge the GeoDataFrames
    if len(gdfs) > 1:
        merged_gdf = gpd.GeoDataFrame(pd.concat(gdfs, ignore_index=True))
    else:
        merged_gdf = gdfs[0]
    
    return merged_gdf

def append_geodataframes(target_gdf, append_gdfs):
    # Ensure target_gdf is a GeoDataFrame
    if not isinstance(target_gdf, gpd.GeoDataFrame):
        raise ValueError("target_gdf must be a GeoDataFrame")

    # Ensure append_gdfs is a list of GeoDataFrames
    if not all(isinstance(gdf, gpd.GeoDataFrame) for gdf in append_gdfs):
        raise ValueError("All elements in append_gdfs must be GeoDataFrames")

    # Get the CRS (coordinate reference system) of the target GeoDataFrame
    target_crs = target_gdf.crs

    # Iterate over each GeoDataFrame in the append_gdfs list
    for gdf in append_gdfs:
        # Reproject the GeoDataFrame to the CRS of the target GeoDataFrame
        if gdf.crs != target_crs:
            gdf = gdf.to_crs(target_crs)

        # Find columns that match in name and data type
        matching_columns = []
        for col in target_gdf.columns:
            if col in gdf.columns:
                if target_gdf[col].dtype == gdf[col].dtype:
                    matching_columns.append(col)

        # Concatenate the matching columns
        target_gdf = pd.concat([target_gdf, gdf[matching_columns]], ignore_index=True)

    return target_gdf
