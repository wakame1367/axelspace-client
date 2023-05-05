import pytest
from datetime import datetime
from pathlib import Path
from grus import MSIFileInfo, parse_filename, gen_geotiff_paths, MSIImageType


@pytest.fixture
def grus_root_path(assets_path):
    return assets_path / "GRUS1A_20210716005528"


@pytest.fixture
def get_msi_image_paths(grus_root_path):
    gen_paths = gen_geotiff_paths(grus_root_path)
    msi_image_paths = []
    for path in gen_paths:
        if isinstance(path, MSIFileInfo):
            msi_image_paths.append(path)
    return msi_image_paths


def test_pan_and_msi_image_paths(get_msi_image_paths):
    msi_image_paths = get_msi_image_paths
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
                break
        break

    common_params = {
        "satellite_name": "GRUS1A",
        "acquisition_datetime": datetime(2021, 7, 16, 0, 55, 28),
        "product_level": "L3A",
        "cell_id": "N43182307",
    }
    msi_valid_file = MSIFileInfo(
        **common_params, image_type=MSIImageType("MSI"), filepath=msi_path.filepath
    )
    pan_valid_file = MSIFileInfo(
        **common_params, image_type=MSIImageType("PAN"), filepath=pan_path.filepath
    )

    assert msi_valid_file == msi_path
    assert pan_valid_file == pan_path
    assert msi_path.is_pan_msi_unique_image(pan_path)
