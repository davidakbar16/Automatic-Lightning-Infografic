import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
from shapely.geometry import Point, box
import numpy as np
from rasterio.transform import from_origin
from rasterio.features import geometry_mask
import cartopy.crs as ccrs
from matplotlib.colors import LinearSegmentedColormap
from scipy.ndimage import gaussian_filter
from matplotlib.patches import Patch

# === 1. BACA DATA PETIR (.txt)
df = pd.read_csv("D:/06. Petir/24-30ap.txt", sep="\t")
geometry = [Point(xy) for xy in zip(df["Longitude"], df["Latitude"])]
gdf_petir = gpd.GeoDataFrame(df, geometry=geometry, crs="EPSG:4326")

# === 2. BACA BATAS WILAYAH DAN CLIP
gdf_wilayah = gpd.read_file("D:/06. Petir/Batas_Wilayah_Administrasi__Area_.shp").to_crs("EPSG:4326")
gdf_petir_clip = gpd.clip(gdf_petir, gdf_wilayah)

# === 3. BACA DATA KEpadatan Penduduk (shapefile dengan gridcode)
gdf_penduduk = gpd.read_file("D:/06. Petir/Kepadatanpenduduk/RasterT_MLClass1_Dissolve.shp").to_crs("EPSG:4326")


# === 4. SPATIAL JOIN antara petir hasil clip dan penduduk
gdf_joined = gpd.sjoin(gdf_petir_clip, gdf_penduduk[["geometry", "gridcode"]], how="left", predicate="intersects")



# === 5. MODIFIKASI SUM BERDASARKAN GRIDCODE
def adjust_sum(row):
    if pd.isna(row["gridcode"]):
        return row["SUM"]
    elif row["gridcode"] == 1:
        return row["SUM"] * 2
    else:
        return row["SUM"]

gdf_joined["SUM_MODIF"] = gdf_joined.apply(adjust_sum, axis=1)

# === 6. RASTER GRID dari SUM_MODIF
# === 6. RASTER GRID dari SUM_MODIF dengan Gaussian smoothing
grid_res = 0.01
minx, miny, maxx, maxy = gdf_wilayah.total_bounds
width = int(np.ceil((maxx - minx) / grid_res))
height = int(np.ceil((maxy - miny) / grid_res))
transform = from_origin(minx, maxy, grid_res, grid_res)

# Buat grid kosong
raster = np.zeros((height, width), dtype=float)
count_grid = np.zeros((height, width), dtype=int)

# Hitung indeks grid
gdf_joined["grid_x"] = ((gdf_joined.geometry.x - minx) // grid_res).astype(int)
gdf_joined["grid_y"] = ((maxy - gdf_joined.geometry.y) // grid_res).astype(int)

# Isi grid dengan SUM_MODIF
for _, row in gdf_joined.iterrows():
    x_idx = row["grid_x"]
    y_idx = row["grid_y"]
    if 0 <= y_idx < height and 0 <= x_idx < width:
        raster[y_idx, x_idx] += row["SUM_MODIF"]
        count_grid[y_idx, x_idx] += 1

# Opsional: Hitung rata-rata jika diperlukan
# raster = np.divide(raster, count_grid, out=np.zeros_like(raster), where=count_grid != 0)

# Terapkan smoothing agar kontur tidak putus-putus
raster_smooth = gaussian_filter(raster, sigma=1)  # sigma bisa disesuaikan (misalnya 0.5–2)


# === 7. MASKING DI LUAR DARATAN
# === 7. MASKING DI LUAR DARATAN (gunakan raster_smooth)
pulau_geom = gdf_wilayah.geometry.unary_union
mask = geometry_mask([pulau_geom], transform=transform, invert=True, out_shape=raster.shape)
raster_masked = np.where(mask, raster_smooth, np.nan)  # gunakan raster_smooth di sini


# === 8. VISUALISASI KONTUR
fig = plt.figure(figsize=(10, 12), facecolor="white")
ax = plt.axes(projection=ccrs.PlateCarree())
ax.set_extent([minx, maxx, miny, maxy])
ax.set_aspect('equal')
# Colormap
cmap = LinearSegmentedColormap.from_list("risk_index", ["#006400", "#ADFF2F", "orange", "red"], N=256)

# Grid koordinat
x = np.linspace(minx, maxx, raster.shape[1])
y = np.linspace(maxy, miny, raster.shape[0])
X, Y = np.meshgrid(x, y)


# Latar: daratan hijau tua
ax.add_geometries([pulau_geom], crs=ccrs.PlateCarree(), facecolor="#006400", edgecolor="none", zorder=1)

# Laut: putih
bounding_box = box(minx, miny, maxx, maxy)
ocean_poly = gpd.GeoSeries([bounding_box], crs="EPSG:4326").difference(pulau_geom)
for geom in ocean_poly:
    ax.add_geometries([geom], crs=ccrs.PlateCarree(), facecolor="#063851", edgecolor="none", zorder=0)

# Plot kontur indeks kerawanan
# Plot kontur indeks kerawanan (gunakan raster_masked hasil smoothing)
ax.contourf(X, Y, raster_masked, levels=100, cmap=cmap, transform=ccrs.PlateCarree(), zorder=2)

# Batas wilayah dan label
gdf_wilayah.boundary.plot(ax=ax, edgecolor="black", linewidth=0.8, zorder=3)
gdf_wilayah["center"] = gdf_wilayah.geometry.centroid
for _, row in gdf_wilayah.iterrows():
    if row["WADMKK"] == "Tapanuli Tengah" and row["center"].distance(pulau_geom) < 0.5:
        continue
    ax.text(row["center"].x, row["center"].y, row["WADMKK"], fontsize=12, fontweight='bold',
            color="black", ha="center", va="center", transform=ccrs.PlateCarree(), zorder=4)
    
legend_elements = [
    Patch(facecolor="#006400", edgecolor="black", label="Rendah"),
    Patch(facecolor="#ADFF2F", edgecolor="black", label="Sedang"),
    Patch(facecolor="orange", edgecolor="black", label="Tinggi"),
    Patch(facecolor="red", edgecolor="black", label="Sangat Tinggi")
]

ax.legend(handles=legend_elements, title="Klasifikasi", loc="lower right", fontsize=10, title_fontsize=11, frameon=True)
plt.tight_layout()
plt.savefig("peta_indeks_kerawanan_petir.png", dpi=300, bbox_inches="tight", facecolor="white")
plt.show()
