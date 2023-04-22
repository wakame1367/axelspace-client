import logging
import rasterio
import pandas as pd
import geopandas as gpd
from pathlib import Path
from datetime import datetime
from pydantic import BaseModel
from enum import Enum
from shapely.geometry import box


logging.basicConfig()
LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.INFO)

ROOT_PATH = Path(__file__).parent
ASSETS_PATH = ROOT_PATH / "assets"


class TCIImageType(str, Enum):
    # トゥルーカラー画像製品(TCI)
    PSM = "PSM"
    PSM_UDM = "PSM_UDM"


class MSIImageType(str, Enum):
    # マルチスペクトル画像製品(MSI)
    PAN = "PAN"
    MSI = "MSI"
    PAN_UDM = "PAN_UDM"
    MSI_UDM = "MSI_UDM"


def is_valid_image_type(image_type, ImageType: MSIImageType) -> bool:
    return image_type in ImageType.__members__.values()


class GrusFileInfo(BaseModel):
    satellite_name: str
    acquisition_datetime: datetime
    product_level: str
    cell_id: str


class MSIFileInfo(GrusFileInfo):
    image_type: MSIImageType


class TCIFileInfo(GrusFileInfo):
    image_type: TCIImageType


def spectral_band_min_max(band_id: int):
    spectral_bands = pd.read_csv(ASSETS_PATH / "grus1_spectral_bands.csv")
    return spectral_bands.loc[band_id, "min"], spectral_bands.loc[band_id, "max"]


def parse_filename(filename: str) -> MSIFileInfo:
    parts = filename.split("_")

    LOGGER.debug(parts)

    cell_id = parts[-1]
    if len(parts) == 5:
        image_type = parts[3]
    elif len(parts) == 6:
        image_type = parts[3] + "_" + parts[4]
    else:
        LOGGER.error(parts)
        raise ValueError("Invalid filename")

    acquisition_datetime = datetime.strptime(parts[1], "%Y%m%d%H%M%S")

    params = {
        "satellite_name": parts[0],
        "acquisition_datetime": acquisition_datetime,
        "product_level": parts[2],
        "image_type": image_type,
        "cell_id": cell_id,
    }

    if is_valid_image_type(image_type, MSIImageType):
        return MSIFileInfo(**params)
    else:
        return TCIFileInfo(**params)


def gen_geotiff_paths(root: Path):
    for path in root.rglob("*.tif"):
        yield parse_filename(path.stem)


def tiff_to_geojson(tiff_file, dst_path: Path) -> None:
    with rasterio.open(tiff_file) as src:
        # GeoTIFFの範囲を取得
        bounds = src.bounds
        # 空間参照系を取得
        crs = src.crs

    # 範囲をshapelyのbox形式に変換
    aoi = box(*bounds)

    # GeoDataFrameの作成
    gdf = gpd.GeoDataFrame({"geometry": [aoi]}, crs=crs)
    gdf = gdf.to_crs("epsg:4326")

    # ポリゴンをGeoJSON形式で書き出す
    gdf.to_file(dst_path, driver="GeoJSON")
