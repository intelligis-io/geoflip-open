import geopandas as gpd

def apply_clip(input_gdf, clipping_gdf):
    """
    Apply a clip transformation to a GeoDataFrame using a clipping GeoDataFrame.

    Parameters:
    input_gdf (gpd.GeoDataFrame): Input geodataframe.
    clipping_gdf (gpd.GeoDataFrame): Clipping geodataframe.
    
    Returns:
    gpd.GeoDataFrame: GeoDataFrame with geometry clipped by the clipping geodataframe.
    """
    clipped_gdf = gpd.clip(input_gdf, clipping_gdf)

    return gpd.GeoDataFrame(clipped_gdf, crs=clipped_gdf.crs)