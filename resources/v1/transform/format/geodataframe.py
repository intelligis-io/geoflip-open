import os
import zipfile
from pyproj.exceptions import CRSError
import json
from pyproj import CRS


def to_shp(input_gdf, schema, output_dir, output_crs="EPSG:4326"):
    # reproject to output crs
    try:
        input_gdf = input_gdf.to_crs(output_crs)
    except CRSError:
        raise CRSError(f"Invalid output crs: {output_crs}")

    # Determine the geometry type after transformation
    new_geom_type = input_gdf.geometry.iloc[0].geom_type if not input_gdf.empty else None

    # Update the schema to reflect the new geometry type (Polygon, MultiPolygon, etc.)
    if new_geom_type and schema is not None:
        schema['geometry'] = new_geom_type

    # Create a shapefile for each aggregated geometry type
    for geom_types, shapefile_name in [
        (['Point', 'MultiPoint'], 'Point'),
        (['LineString', 'MultiLineString'], 'LineString'),
        (['Polygon', 'MultiPolygon'], 'Polygon')
    ]:
        # Filter to the specified geometry types
        gdf_filtered = input_gdf[input_gdf.geometry.type.isin(geom_types)]
        if not gdf_filtered.empty:
            shapefile_path = os.path.join(output_dir, f"{shapefile_name}.shp")
            gdf_filtered.to_file(shapefile_path, schema=schema, driver="ESRI Shapefile", engine="fiona")

    # create zip file
    output_filename = "geoflip"
    shapefile_extensions = ['.shp', '.shx', '.dbf', '.prj', '.cpg', '.qix']
    zip_file_path = os.path.join(output_dir, f"{output_filename}.zip")
    compression_method = zipfile.ZIP_DEFLATED
    with zipfile.ZipFile(zip_file_path, 'w', compression=compression_method) as zipf:
        for file in os.listdir(output_dir):
            root, ext = os.path.splitext(file)
            if ext in shapefile_extensions:
                zipf.write(os.path.join(output_dir, file), arcname=file)
    
    return zip_file_path

def to_gpkg(input_gdf, output_dir, output_crs="EPSG:4326"):
    try:
        input_gdf = input_gdf.to_crs(output_crs)
    except CRSError:
        raise CRSError(f"Invalid output crs: {output_crs}")
    
    geopackage_path = os.path.join(output_dir, "geoflip.gpkg")

    try:
        input_gdf.to_file(geopackage_path, driver="GPKG")
    #  Handle the case where the FID column is missing or has duplicates
    except RuntimeError:
        # List of possible FID column names
        fid_columns = ['FID', 'fid', 'Fid']
        
        # Find the FID column if it exists
        fid_col = next((col for col in fid_columns if col in input_gdf.columns), None)
        
        if fid_col:
            # Check if the FID column has duplicates
            if input_gdf[fid_col].duplicated().any():
                # Remove the FID column
                input_gdf = input_gdf.drop(columns=[fid_col])
                # Reset the index to create a new unique FID
                input_gdf = input_gdf.reset_index(drop=True)
                # Add a new FID column with unique values
                input_gdf['fid'] = range(len(input_gdf))
        else:
            # If no FID column exists, create one
            input_gdf['fid'] = range(len(input_gdf))
        
        input_gdf.to_file(geopackage_path, driver="GPKG")

    return geopackage_path

def to_dxf(input_gdf, output_dir, output_crs="EPSG:4326"):
    # Reproject to output CRS
    try:
        input_gdf = input_gdf.to_crs(output_crs)
    except CRSError:
        raise CRSError(f"Invalid output crs: {output_crs}")

    # Create a new GeoDataFrame with only the geometry column
    geom_only_gdf = input_gdf[['geometry']]

    dxf_path = os.path.join(output_dir, "geoflip.dxf")
    
    # Write the geometry-only GeoDataFrame to a DXF file
    geom_only_gdf.to_file(dxf_path, driver="DXF")

    return dxf_path

def to_geojson(input_gdf, output_dir):
    try:
        input_gdf = input_gdf.to_crs("EPSG:4326")
        geojson_path = os.path.join(output_dir, "geoflip.geojson")
        input_gdf.to_file(geojson_path, driver="GeoJSON")
    except Exception as e:
        raise Exception(f"Error converting to GeoJSON: {e}")
    
    return geojson_path

def to_csv(input_gdf, output_dir, output_crs="EPSG:4326"):
    try:
        # Reproject to the specified output CRS
        input_gdf = input_gdf.to_crs(output_crs)
    except CRSError:
        raise CRSError(f"Invalid output crs: {output_crs}")

    csv_file_path = os.path.join(output_dir, "geoflip.csv")

    try:
        # Convert geometry to WKT
        input_gdf["geometry"] = input_gdf["geometry"].apply(lambda geom: geom.wkt)

        # Save as CSV
        input_gdf.to_csv(csv_file_path, index=False)

    except Exception as e:
        raise Exception(f"Error converting to CSV: {e}")

    return csv_file_path

def convert_shapely_to_esri(geometry):
    """
    Convert a Shapely geometry object into EsriJSON geometry.
    - Points => {"x": ..., "y": ...}
    - MultiPoint => {"points": [[x1, y1], [x2, y2], ...]}
    - LineString => {"paths": [ [[x1, y1], [x2, y2], ...] ]}
    - MultiLineString => {"paths": [ [[x1, y1], [x2, y2]], [[x3, y3]...] ]}
    - Polygon => {"rings": [ [ [x1, y1], [x2, y2], ... ] ]}
    - MultiPolygon => {"rings": [...multiple rings...]}
    """

    # Handle empty geometries up front
    if geometry.is_empty:
        return {
            "type": "GeometryCollection",
            "geometries": []
        }

    geom_type = geometry.geom_type

    match geom_type:
        case "Point":
            return {
                "x": geometry.x,
                "y": geometry.y
            }
        
        case "MultiPoint":
            # In Esri JSON, multi-points can be given as:
            #  {"points": [[x1, y1], [x2, y2], ...]}
            coords = list(geometry.coords)  # or geometry.geoms in shapely 2.0
            return {
                "points": [[x, y] for x, y in coords]
            }
        
        case "LineString":
            coords = list(geometry.coords)
            return {
                "paths": [coords]
            }
        
        case "MultiLineString":
            # Each sub-line is one path
            paths = [list(linestring.coords) for linestring in geometry.geoms]
            return {
                "paths": paths
            }
        
        case "Polygon":
            # A polygon's 'rings' are [exterior_coords, *interior_coords]
            rings = []
            # Exterior ring
            rings.append(list(geometry.exterior.coords))
            # Interior rings (holes)
            for ring in geometry.interiors:
                rings.append(list(ring.coords))
            return {
                "rings": rings
            }
        
        case "MultiPolygon":
            # For a multi-polygon, we'll flatten out all exteriors and interiors
            # into a single 'rings' array. ArcGIS typically interprets these
            # as multiple polygon parts within a single feature.
            rings = []
            for poly in geometry.geoms:
                rings.append(list(poly.exterior.coords))
                for ring in poly.interiors:
                    rings.append(list(ring.coords))
            return {
                "rings": rings
            }

        # Catch-all for any geometry type we haven't explicitly handled (e.g., GeometryCollection)
        case _:
            return {
                "type": "GeometryCollection",
                "geometries": []
            }

def create_esrijson_from_gdf(input_gdf, output_crs):
    try:
        crs_obj = CRS.from_string(output_crs)
        # This works if the CRS has an authority code (like EPSG).
        # If not, fallback to something else or raise an error.
        wkid = crs_obj.to_authority()[1]  # e.g. ('EPSG', '4326') => '4326'
        wkid = int(wkid)
    except Exception:
        raise Exception(f"Error converting to esrijson, output_crs is not valid: {output_crs}")
        
    # Build the Esri FeatureSet
    esrijson_data = {
        "spatialReference": {"wkid": wkid},
        "features": []
    }

    # Iterate each row in the GeoDataFrame
    for idx, row in input_gdf.iterrows():
        # Convert all non-geometry fields to attributes
        attributes = row.to_dict()
        # Remove the geometry column from attributes
        geometry_shapely = attributes.pop(input_gdf.geometry.name)

        # Convert the shapely geometry to Esri geometry dict
        esri_geom = convert_shapely_to_esri(geometry_shapely)

        feature = {
            "attributes": attributes,
            "geometry": esri_geom
        }
        esrijson_data["features"].append(feature)
    
    return esrijson_data

def to_esrijson(input_gdf, output_dir, output_crs="EPSG:4326"):
    try:
        # Reproject to the specified output CRS
        input_gdf = input_gdf.to_crs(output_crs)
    except CRSError:
        raise CRSError(f"Invalid output crs: {output_crs}")
    esrijson_file_path = os.path.join(output_dir, "geoflip.esrijson")

    try:
        esrijson_data = create_esrijson_from_gdf(input_gdf, output_crs)

        # Write out the EsriJSON file
        with open(esrijson_file_path, "w") as f:
            json.dump(esrijson_data, f)

    except Exception as e:
        raise Exception(f"Error converting to esrijson: {e}")

    return esrijson_file_path
