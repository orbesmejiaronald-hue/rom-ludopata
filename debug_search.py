import requests
from bs4 import BeautifulSoup
import urllib.parse
import re

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
}
url = "https://html.duckduckgo.com/html/?q=Real+Madrid"
response = requests.get(url, headers=headers)
print("Status code:", response.status_code)
print("HTML length:", len(response.text))

soup = BeautifulSoup(response.text, "html.parser")

# Imprimir todas las clases de enlaces de resultado para inspeccionar
links = soup.find_all("a")
print("Total links found:", len(links))

# Buscar enlaces que contengan redirección de DDG o que tengan clases específicas
results_found = 0
for a in links:
    href = a.get("href", "")
    text = a.get_text(strip=True)
    if "uddg=" in href or ("duckduckgo.com/l/?" in href):
        results_found += 1
        print(f"Link {results_found}: text={text[:40]} | href={href[:100]}")
        if results_found >= 5:
            break

if results_found == 0:
    # Si no se encontraron, veamos si hay algún contenedor clásico
    print("\nPrimeros 1000 caracteres de HTML:")
    print(response.text[:1000])
