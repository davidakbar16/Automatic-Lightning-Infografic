import geopandas as gpd
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

from shapely.geometry import Point

# 1. Load shapefile batas wilayah administratif Pulau Nias
shapefile_path = "F:/03.PENGOLAHAN PETIR MINGGUAN/Batas_Wilayah_Administrasi__Area_.shp"
gdf_wilayah = gpd.read_file(shapefile_path)

# 2. Load data sambaran petir
file_path = "D:/06. Petir/24-30ap.txt"
df = pd.read_csv(file_path, delimiter='\t', header=None, names=['Waktu', 'Jenis', 'Longitude', 'Latitude'])

# 3. Pastikan kolom numerik
df['Longitude'] = pd.to_numeric(df['Longitude'], errors='coerce')
df['Latitude'] = pd.to_numeric(df['Latitude'], errors='coerce')
df = df.dropna(subset=['Longitude', 'Latitude'])

# 4. Ubah DataFrame menjadi GeoDataFrame (titik petir)
geometry = [Point(xy) for xy in zip(df['Longitude'], df['Latitude'])]
gdf_petir = gpd.GeoDataFrame(df, geometry=geometry, crs=gdf_wilayah.crs)

# 5. Spatial join: hanya titik yang jatuh di wilayah daratan (poligon)
joined = gpd.sjoin(gdf_petir, gdf_wilayah, how='inner', predicate='within')  # hanya di dalam daratan

# 6. Hitung sambaran per wilayah
summary = (
    joined.groupby(['NAMOBJ', 'Jenis'])
    .size()
    .unstack(fill_value=0)
    .reset_index()
)

# 7. Hitung total sambaran
summary['Jumlah'] = summary.get('Positive Cloud to Ground', 0) + summary.get('Negative Cloud to Ground', 0)

# 8. Buat grafik batang horizontal
summary = summary.sort_values('Jumlah', ascending=True)

fig, ax = plt.subplots(figsize=(12, 8))

# Set background biru
fig.patch.set_facecolor('#063851')  # latar belakang keseluruhan
ax.set_facecolor('#063851')         # latar belakang area grafik

bar_width = 0.25
index = np.arange(len(summary))

ax.barh(index, summary['Jumlah'], bar_width, label='Jumlah', color='gray')
ax.barh(index + bar_width, summary.get('Negative Cloud to Ground', 0), bar_width, label='CG-', color='red')
ax.barh(index + 2*bar_width, summary.get('Positive Cloud to Ground', 0), bar_width, label='CG+', color='orange')

ax.set_yticks(index + bar_width)
ax.set_yticklabels(summary['NAMOBJ'])
ax.set_xlabel('Jumlah Sambaran Petir')
ax.set_title('Grafik Sambaran Petir per Kabupaten/Kota\n(24-30 April 2025)', fontsize=14)
ax.legend()

# 9. Tambahkan baris TOTAL ke summary
total_row = pd.DataFrame({
    'NAMOBJ': ['TOTAL'],
    'Jumlah': [summary['Jumlah'].sum()],
    'Negative Cloud to Ground': [summary.get('Negative Cloud to Ground', 0).sum()],
    'Positive Cloud to Ground': [summary.get('Positive Cloud to Ground', 0).sum()]
})

summary_with_total = pd.concat([summary, total_row], ignore_index=True)

# Siapkan isi tabel dan label
cell_text = summary_with_total[['Jumlah', 'Negative Cloud to Ground', 'Positive Cloud to Ground']].values.tolist()
row_labels = summary_with_total['NAMOBJ']
col_labels = ['JUMLAH', 'CG-', 'CG+']

# Tambahkan tabel
table = plt.table(
    cellText=cell_text,
    rowLabels=row_labels,
    colLabels=col_labels,
    loc='bottom',
    cellLoc='center',
    rowLoc='center',
    bbox=[0.0, -0.55, 1, 0.4]  # Atur posisi agar muat
)

# Set font size
table.auto_set_font_size(False)
table.set_fontsize(9)

# 🔵 Ubah warna latar belakang tabel menjadi biru laut
for key, cell in table.get_celld().items():
    cell.set_facecolor('#063851')   # Warna biru laut
    cell.set_text_props(color='white')  # Agar teks kontras
# Ubah warna teks pada sumbu dan judul menjadi putih
ax.title.set_color('white')
ax.xaxis.label.set_color('white')
ax.yaxis.label.set_color('white')
ax.tick_params(axis='x', colors='white')
ax.tick_params(axis='y', colors='white')

# Ubah warna label legenda menjadi putih
legend = ax.get_legend()
for text in legend.get_texts():
    text.set_color('white')

# Geser ruang agar tabel tidak menabrak
plt.subplots_adjust(left=0.2, bottom=0.3)
plt.tight_layout()
plt.show()