import logging
import pandas as pd
from pathlib import Path
from datetime import datetime
from pydantic import BaseModel
from enum import Enum
from typing import Tuple, Union
from collections.abc import Generator


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


class FileInfo(BaseModel):
    filepath: Path


class GrusFileInfo(FileInfo):
    satellite_name: str
    acquisition_datetime: datetime
    product_level: str
    cell_id: str


class MSIFileInfo(GrusFileInfo):
    image_type: MSIImageType

    def is_pan_msi_unique_image(cls, other: "MSIFileInfo") -> bool:
        # 撮影日が同じかつCellIDが同じである、MSIとPAN画像であるか
        # UDMファイルは対象外
        if other.image_type == "PAN_UDM" or other.image_type == "MSI_UDM":
            return False
        if cls.image_type == "PAN_UDM" or cls.image_type == "MSI_UDM":
            return False

        is_unique_cell_id = cls.cell_id == other.cell_id
        is_equal_datetime = cls.acquisition_datetime == other.acquisition_datetime
        not_equal_image_type = cls.image_type != other.image_type
        is_pan_and_msi = (cls.image_type == "MSI" and other.image_type == "PAN") or (
            cls.image_type == "PAN" and other.image_type == "MSI"
        )

        LOGGER.debug(f"is_unique_cell_id : {is_unique_cell_id}")
        LOGGER.debug(f"is_equal_datetime : {is_equal_datetime}")
        LOGGER.debug(f"not_equal_image_type : {not_equal_image_type}")
        LOGGER.debug(f"is_pan_and_msi : {is_pan_and_msi}")

        return all(
            [is_unique_cell_id, is_equal_datetime, not_equal_image_type, is_pan_and_msi]
        )


class TCIFileInfo(GrusFileInfo):
    image_type: TCIImageType


def spectral_band_min_max(band_id: int):
    spectral_bands = pd.read_csv(ASSETS_PATH / "grus1_spectral_bands.csv")
    return spectral_bands.loc[band_id, "min"], spectral_bands.loc[band_id, "max"]


def parse_filename(filepath: Path) -> Union[MSIFileInfo, TCIFileInfo]:
    filename = filepath.stem
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
        "filepath": filepath,
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


def gen_geotiff_paths(root: Path) -> Generator[Union[MSIFileInfo, TCIFileInfo]]:
    for path in root.rglob("*.tif"):
        yield parse_filename(path)


def get_each_equal_pan_and_msi_path(
    root_path: Path,
) -> Generator[Tuple[MSIFileInfo, TCIFileInfo]]:
    """_summary_
    撮影日とCellIDが同じであるPANとMSI画像のGeoTIFFファイルパスをgeneratorで返す

    Args:
        root_path (Path): _description_

    Yields:
        _type_: _description_
    """
    gen_paths = gen_geotiff_paths(root_path)
    msi_image_paths = []
    for path in gen_paths:
        if isinstance(path, MSIFileInfo):
            msi_image_paths.append(path)

    msi_paths = []
    pan_paths = []

    for path in msi_image_paths:
        if path.image_type == "PAN":
            pan_paths.append(path)
        elif path.image_type == "MSI":
            msi_paths.append(path)

    for msi_path in msi_paths:
        for pan_path in pan_paths:
            if msi_path.is_pan_msi_unique_image(pan_path):
                yield msi_path, pan_path
