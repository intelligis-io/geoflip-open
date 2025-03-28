import geopandas as gpd


def apply_dissolve(input_gdf, by):
    """
    Dissolve the input GeoDataFrame based on the specified attribute.

    Parameters:
    input_gdf (GeoDataFrame): The input GeoDataFrame to be dissolved.
    by (str or list): Column or list of columns to group by.

    Returns:
    GeoDataFrame: A new GeoDataFrame with dissolved geometries.
    """

    print(by)
    # Perform the dissolve operation
    dissolved_gdf = input_gdf.dissolve(by=by)
    
    # Return the result GeoDataFrame
    return gpd.GeoDataFrame(dissolved_gdf, crs=input_gdf.crs)
