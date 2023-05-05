import rasterio
import geopandas as gpd
from shapely.geometry import box


def tiff_to_geojson(tiff_file) -> gpd.GeoDataFrame:
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
    # gdf.to_file(dst_path, driver="GeoJSON")
    return gdf
