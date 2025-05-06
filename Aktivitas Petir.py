import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
from shapely.geometry import Point, box
import numpy as np
import rasterio
from rasterio.transform import from_origin
from rasterio.features import geometry_mask
import cartopy.crs as ccrs
from matplotlib.colors import LinearSegmentedColormap

# === 1. BACA DATA
df = pd.read_csv("D:/06. Petir/test.txt", sep="\t")
df = df.rename(columns={"Tanggal (UTC)": "Waktu", "Jenis": "Jenis", "Bujur": "Longitude", "Lintang": "Latitude"})
geometry = [Point(xy) for xy in zip(df["Longitude"], df["Latitude"])]
gdf_petir = gpd.GeoDataFrame(df, geometry=geometry, crs="EPSG:4326")

gdf_wilayah = gpd.read_file("D:/06. Petir/Batas_Wilayah_Administrasi__Area_.shp").to_crs("EPSG:4326")
gdf_pulau = gdf_wilayah.geometry.union_all()  # Gantikan unary_union yang deprecated

gdf_petir = gpd.clip(gdf_petir, gdf_wilayah)

# === 2. BUAT GRID RASTER
grid_res = 0.01
minx, miny, maxx, maxy = gdf_wilayah.total_bounds
width = int((maxx - minx) / grid_res)
height = int((maxy - miny) / grid_res)
transform = from_origin(minx, maxy, grid_res, grid_res)

raster = np.zeros((height, width), dtype=int)
col = ((gdf_petir.geometry.x - minx) / grid_res).astype(int)
row = ((maxy - gdf_petir.geometry.y) / grid_res).astype(int)
for r, c in zip(row, col):
    if 0 <= r < height and 0 <= c < width:
        raster[r, c] += 1

# === 3. KLASIFIKASI SMOOTH
raster_clipped = np.clip(raster, 0, 16)
kategori = raster_clipped.astype(float)

# === 4. MASKING DI LUAR DARATAN
mask = geometry_mask([gdf_pulau], transform=transform, invert=True, out_shape=raster.shape)
kategori_masked = np.where(mask, kategori, np.nan)

# === 5. PLOTTING
fig = plt.figure(figsize=(10, 12), facecolor="white")
ax = plt.axes(projection=ccrs.PlateCarree())
ax.set_extent([minx, maxx, miny, maxy], crs=ccrs.PlateCarree())
ax.set_facecolor("white")
ax.set_aspect('equal')

# Colormap smooth
cmap = LinearSegmentedColormap.from_list("petir_cmap", ["#006400", "#ADFF2F", "orange", "red"], N=256)

# Koordinat grid
x = np.arange(minx + grid_res / 1.2, maxx, grid_res)
y = np.arange(maxy - grid_res / 1.2, miny, -grid_res)
X, Y = np.meshgrid(x, y)

# === MASKING LUAR DARATAN PUTIH
bounding_box = box(minx, miny, maxx, maxy)
ocean_poly = gpd.GeoSeries([bounding_box], crs="EPSG:4326").difference(gdf_pulau)

for geom in ocean_poly:
    ax.add_geometries([geom], crs=ccrs.PlateCarree(), facecolor="#063851", edgecolor="none", zorder=0)

# === TAMBAH DARATAN WARNA HIJAU (#006400)
ax.add_geometries([gdf_pulau], crs=ccrs.PlateCarree(), facecolor="#006400", edgecolor="none", zorder=1)

# === PLOTTING SAMBARAN PETIR
contour = ax.contourf(X, Y, kategori_masked, levels=100, cmap=cmap, transform=ccrs.PlateCarree(), zorder=2)

# === BATAS WILAYAH
gdf_wilayah.boundary.plot(ax=ax, edgecolor="black", linewidth=0.8, transform=ccrs.PlateCarree(), zorder=3)

# === LABEL NAMA WILAYAH
gdf_wilayah["center"] = gdf_wilayah.geometry.centroid
for _, row in gdf_wilayah.iterrows():
    # Hilangkan label Tapanuli Tengah yang terlalu dekat dengan Pulau Nias
    if row["WADMKK"] == "Tapanuli Tengah" and row["center"].distance(gdf_pulau) < 0.5:
        continue
    ax.text(
        row["center"].x,
        row["center"].y,
        row["WADMKK"],
        fontsize=12,
        fontweight='bold',
        color="black",
        ha="center",
        va="center",
        transform=ccrs.PlateCarree(),
        zorder=4
    )

# === COLORBAR
plt.tight_layout()
plt.savefig("peta_petir_nias_full.png", dpi=300, bbox_inches="tight", facecolor="white")
plt.show()
