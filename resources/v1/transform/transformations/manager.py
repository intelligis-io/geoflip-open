from .buffer import apply_buffer
from .clip import apply_clip
from .erase import apply_erase
from .dissolve import apply_dissolve
from .union import apply_union
import geopandas as gpd
from utils.logger import get_logger

logger = get_logger(__name__)


class UnsupportedTransformationError(Exception):
    """Exception raised for unsupported transformation types."""

    def __init__(self, transformation_type, message="Unsupported transformation type"):
        self.transformation_type = transformation_type
        self.message = message
        super().__init__(f"{message}: {transformation_type}")


# apply all transformations, the output of each transformation is the input to the next
# TODO: units consumed should be calculated based on the transformations applied
# TODO: this should be refactored to be more modular and extensible
def apply_transformations(gdf, request_data: dict):
    """Apply transformations to a GeoDataFrame based on the request data."""
    transformations_applied = []
    output_gdf = gdf
    for transform in request_data["transformations"]:
        match transform["type"]:
            case "buffer":
                distance = transform["distance"]
                units = transform["units"]

                try:
                    simplify_tolerance = transform["simplify_tolerance"]
                except KeyError:
                    # setting this to none will use the default value in apply_buffer
                    # of 3% of the buffer distance
                    simplify_tolerance = None

                output_gdf = apply_buffer(output_gdf, distance, units, simplify_tolerance=simplify_tolerance)

                # calculate units consumed for buffers
                transformations_applied.append("buffer")
            case "clip":
                clipping_gdf = gpd.GeoDataFrame.from_features(
                    transform["clipping_geojson"], crs="EPSG:4326"
                )
                output_gdf = apply_clip(output_gdf, clipping_gdf)

                # calculate units consumed for clips
                transformations_applied.append("clip")
            case "erase":
                erasing_gdf = gpd.GeoDataFrame.from_features(
                    transform["erasing_geojson"], crs="EPSG:4326"
                )
                output_gdf = apply_erase(output_gdf, erasing_gdf)

                # calculate units consumed for clips
                transformations_applied.append("erase")
            case "dissolve":
                by = transform["by"]
                output_gdf = apply_dissolve(output_gdf, by)

                # calculate units consumed for dissolve
                transformations_applied.append("dissolve")
            case "union":
                output_gdf = apply_union(output_gdf)

                # calculate units consumed for dissolve
                transformations_applied.append("union")
            case _:
                logger.error(f"Unsupported transformation type: {transform['type']}")
                raise UnsupportedTransformationError(transform["type"])

    return output_gdf, transformations_applied
