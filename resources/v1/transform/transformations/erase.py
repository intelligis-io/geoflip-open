import geopandas as gpd


def apply_erase(input_gdf, erase_gdf):
    
    # Ensure both GeoDataFrames are in the same CRS
    if input_gdf.crs != erase_gdf.crs:
        erase_gdf = erase_gdf.to_crs(input_gdf.crs)
    
    # Perform the erase operation
    erased_gdf = gpd.overlay(input_gdf, erase_gdf, how='difference')

    # Return the result GeoDataFrame
    return gpd.GeoDataFrame(erased_gdf, crs=erased_gdf.crs)
