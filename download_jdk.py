import os
import zipfile
import requests

url = "https://api.adoptium.net/v3/binary/latest/17/ga/windows/x64/jdk/hotspot/normal/eclipse?project=jdk"
zip_path = "jdk17.zip"
extract_path = "jdk17"

print("Descargando JDK 17 desde Adoptium API...")
r = requests.get(url, stream=True)
if r.status_code == 200:
    with open(zip_path, 'wb') as f:
        for chunk in r.iter_content(chunk_size=8192):
            f.write(chunk)
    print("Descarga completa. Extrayendo archivos...")
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_path)
    print("Extracción completa.")
    os.remove(zip_path)
else:
    print(f"Error al descargar: {r.status_code}")
