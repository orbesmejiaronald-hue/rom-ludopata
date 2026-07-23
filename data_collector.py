import os
import re
import json
import urllib.parse
import requests
from bs4 import BeautifulSoup

class DataCollector:
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
        }

    def search_duckduckgo(self, query: str, max_results: int = 5):
        """
        Busca en DuckDuckGo usando la librería oficial 'duckduckgo_search' (DDGS) de forma gratuita.
        Soporta fallback a raspado HTML si falla.
        """
        import time
        import random
        
        print(f"[DataCollector] Buscando en internet: '{query}'...")
        time.sleep(random.uniform(0.1, 0.5))
        
        # Intento 1: Usar DDGS de la librería oficial ddgs / duckduckgo_search
        try:
            try:
                from ddgs import DDGS
            except ImportError:
                from duckduckgo_search import DDGS
            with DDGS() as ddgs:
                raw_results = list(ddgs.text(query, max_results=max_results))
                if raw_results:
                    formatted_results = []
                    for item in raw_results:
                        formatted_results.append({
                            "url": item.get("href") or item.get("url", ""),
                            "snippet": item.get("body") or item.get("snippet", "")
                        })
                    if formatted_results:
                        return formatted_results
        except Exception as e:
            print(f"[DataCollector] Advertencia con DDGS ({e}). Intentando fallback a raspado HTML...")
        
        # Intento 2: Fallback a raspado directo HTML
        url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}"
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36"
        ]
        
        for attempt in range(3):
            try:
                headers = {
                    "User-Agent": user_agents[attempt % len(user_agents)],
                    "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
                }
                response = requests.get(url, headers=headers, timeout=10)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, "html.parser")
                    results = []
                    seen_urls = set()
                    
                    for a in soup.find_all("a", href=re.compile(r"uddg=")):
                        href = a.get("href")
                        match = re.search(r"uddg=(https?://[^&]+)", href)
                        if not match:
                            match = re.search(r"uddg=(https?%3A%2F%2F[^&]+)", href)
                            
                        if match:
                            actual_url = urllib.parse.unquote(match.group(1))
                            if actual_url in seen_urls:
                                continue
                                
                            parent = a.find_parent("div", class_=re.compile(r"result"))
                            snippet = ""
                            if parent:
                                snippet_el = parent.find(class_=re.compile(r"snippet"))
                                if snippet_el:
                                    snippet = snippet_el.get_text(strip=True)
                            
                            if not snippet and len(a.get_text(strip=True)) > 20:
                                snippet = a.get_text(strip=True)
                                
                            seen_urls.add(actual_url)
                            results.append({
                                "url": actual_url,
                                "snippet": snippet
                            })
                            if len(results) >= max_results:
                                break
                    if results:
                        return results
                    
                print(f"[DataCollector] DuckDuckGo HTML devolvió estado {response.status_code} o sin resultados. Reintentando...")
                time.sleep(1 + random.random())
            except Exception as e:
                print(f"[DataCollector] Error en intento {attempt+1} buscando '{query}': {e}")
                time.sleep(1)
        
        return []

    def fetch_page_text(self, url: str) -> str:
        """
        Obtiene el texto legible de una página web para analizarlo.
        """
        try:
            response = requests.get(url, headers=self.headers, timeout=8)
            if response.status_code != 200:
                return ""
            soup = BeautifulSoup(response.text, "html.parser")
            # Quitar scripts y estilos
            for script in soup(["script", "style", "nav", "footer", "header"]):
                script.decompose()
            text = soup.get_text(separator=" ")
            # Limpiar espacios en blanco
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = " ".join(chunk for chunk in chunks if chunk)
            return text[:4000] # Limitar a 4000 caracteres para evitar saturar el LLM
        except Exception as e:
            print(f"[DataCollector] Error leyendo URL {url}: {e}")
            return ""

    def collect_all_data(self, local_team: str, visitor_team: str) -> dict:
        """
        Recopila toda la información requerida del partido en internet de forma concurrente con alta precisión.
        """
        import concurrent.futures
        
        match_query = f"{local_team} vs {visitor_team}"
        
        queries = {
            "match_info": (f"{match_query} ultimos partidos resultados estadisticas corners tarjetas", 5),
            "lineups": (f"alineaciones confirmadas {match_query} once inicial xi titulares", 5),
            "referee": (f"árbitro {match_query}", 4),
            "stadium_weather": (f"estadio sede {match_query} clima", 4),
            "player_rumors": (f"{match_query} lesionados bajas suspendidos noticias", 4)
        }
        
        search_results = {}
        
        print("[DataCollector] Lanzando búsquedas en vivo de alta precisión...")
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = {
                executor.submit(self.search_duckduckgo, q[0], q[1]): key 
                for key, q in queries.items()
            }
            for future in concurrent.futures.as_completed(futures):
                key = futures[future]
                try:
                    search_results[key] = future.result()
                except Exception as e:
                    print(f"[DataCollector] Error en búsqueda de {key}: {e}")
                    search_results[key] = []
                    
        # Validar snippets de lineups
        lineups_snippets = [res["snippet"] for res in search_results.get("lineups", [])]
        is_confirmed = False
        
        confirmation_keywords = ["confirmada", "confirmadas", "oficial", "oficiales", "once inicial", "11 inicial", "starting xi", "alineación titular", "titulares confirmados", "xi oficial", "once titular"]
        
        valid_lineups_snippets = []
        for snip in lineups_snippets:
            snip_lower = snip.lower()
            if any(kw in snip_lower for kw in confirmation_keywords):
                valid_lineups_snippets.append(snip)
                is_confirmed = True
            elif ("once" in snip_lower or "titulares" in snip_lower or "formación" in snip_lower):
                valid_lineups_snippets.append(snip)
                
        if is_confirmed or valid_lineups_snippets:
            context_lineups = [f"ESTADO DE ALINEACIONES: {'CONFIRMADAS EN VIVO' if is_confirmed else 'ALINEACIONES PREVIAS / PROBABLES Extraídas de Prensa.'}"]
            context_lineups.extend(valid_lineups_snippets)
        else:
            context_lineups = ["ESTADO DE ALINEACIONES: EXTRAER ALINEACIÓN RECIENTE A PARTIR DEL SIGUIENTE TEXTO."]
            context_lineups.extend(lineups_snippets if lineups_snippets else [res["snippet"] for res in search_results.get("match_info", [])])

        referee_snippets = [res["snippet"] for res in search_results.get("referee", [])]
        stadium_snippets = [res["snippet"] for res in search_results.get("stadium_weather", [])]
        
        context = {
            "match_info": [res["snippet"] for res in search_results.get("match_info", [])],
            "lineups": context_lineups,
            "referee": referee_snippets if referee_snippets else ["Información de árbitro no disponible."],
            "stadium_and_weather": stadium_snippets if stadium_snippets else ["Información de estadio no disponible."],
            "player_rumors": [res["snippet"] for res in search_results.get("player_rumors", [])],
            "scraped_pages": []
        }
        
        # Descargar contenido completo de las mejores URLs para evitar alucinaciones
        urls_to_fetch = []
        for l in [search_results.get("lineups", []), search_results.get("referee", []), search_results.get("match_info", [])]:
            if l:
                urls_to_fetch.append(l[0]["url"])
                
        urls_to_fetch = list(dict.fromkeys(urls_to_fetch))[:3]
        
        if urls_to_fetch:
            print(f"[DataCollector] Descargando contenido de {len(urls_to_fetch)} páginas clave...")
            with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
                fetch_futures = {
                    executor.submit(self.fetch_page_text, url): url 
                    for url in urls_to_fetch
                }
                for future in concurrent.futures.as_completed(fetch_futures):
                    url = fetch_futures[future]
                    try:
                        page_text = future.result()
                        if page_text and len(page_text) > 100:
                            context["scraped_pages"].append({
                                "url": url,
                                "content": page_text[:2500]
                            })
                    except Exception as e:
                        print(f"[DataCollector] Error descargando {url}: {e}")
                        
        return context

# Prueba rápida si se ejecuta directamente
if __name__ == "__main__":
    collector = DataCollector()
    data = collector.collect_all_data("Real Madrid", "Barcelona")
    print(json.dumps(data, indent=2, ensure_ascii=False)[:1000])
