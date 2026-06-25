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
        Busca en DuckDuckGo (HTML libre de JavaScript) y extrae enlaces y resúmenes de forma robusta.
        Soporta reintentos y rotación de User-Agent.
        """
        import time
        import random
        
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36"
        ]
        
        print(f"[DataCollector] Buscando en internet: '{query}'...")
        url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}"
        
        # Introducir un pequeño retardo inicial aleatorio para escalonar las peticiones concurrentes
        time.sleep(random.uniform(0.2, 1.2))
        
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
                    
                print(f"[DataCollector] DuckDuckGo devolvió estado {response.status_code} o sin resultados. Reintentando...")
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
        Recopila toda la información requerida del partido en internet de forma concurrente.
        """
        import concurrent.futures
        
        match_query = f"{local_team} vs {visitor_team}"
        
        queries = {
            "match_info": (f"{match_query} últimos partidos resultados estadísticas corners tarjetas flashscore", 4),
            "lineups": (f"{match_query} alineaciones probables esperadas lineups flashscore", 4),
            "referee": (f"{match_query} árbitro designado tarjetas estadísticas", 3),
            "stadium_and_weather": (f"{match_query} estadio nombre ubicación flashscore", 3),
            "realtime_weather_grass": (f"{match_query} tipo de césped clima pronóstico tiempo real", 3),
            "player_rumors": (f"{local_team} {visitor_team} rumores jugadores redes sociales lesiones", 4)
        }
        
        search_results = {}
        
        print("[DataCollector] Lanzando búsquedas concurrentes en internet...")
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
                    
        # Validar rigurosamente los snippets de lineups para asegurar que correspondan a alineaciones oficiales confirmadas
        lineups_snippets = [res["snippet"] for res in search_results.get("lineups", [])]
        is_confirmed = False
        
        # Palabras que indican confirmación real
        confirmation_keywords = ["confirmada", "confirmadas", "oficial", "oficiales", "once inicial", "11 inicial", "starting xi", "lineups confirmed", "alineación titular", "titulares confirmados"]
        # Palabras que indican especulación
        speculative_keywords = ["probable", "probables", "posible", "posibles", "pronóstico", "predicted", "esperadas", "posible alineación"]
        
        valid_lineups_snippets = []
        for snip in lineups_snippets:
            snip_lower = snip.lower()
            
            # Si contiene alguna palabra de confirmación y no es meramente una especulación
            has_confirm = any(kw in snip_lower for kw in confirmation_keywords)
            has_spec = any(kw in snip_lower for kw in speculative_keywords)
            
            # Aceptar si tiene confirmación clara
            if has_confirm or ("once" in snip_lower or "titulares" in snip_lower and not has_spec):
                valid_lineups_snippets.append(snip)
                is_confirmed = True
                
        # Si no pudimos verificar de forma robusta la alineación confirmada en internet
        if not is_confirmed or not valid_lineups_snippets:
            # Mandamos un marcador indicando que no está confirmado, pero agregamos todos los snippets disponibles
            context_lineups = ["ESTADO DE ALINEACIONES: NO CONFIRMADAS EN VIVO. EXTRAER ALINEACIÓN PREVIA O PROBABLE A PARTIR DE LOS SIGUIENTES TEXTOS."]
            context_lineups.extend(lineups_snippets)
            if not lineups_snippets:
                match_info_snippets = [res["snippet"] for res in search_results.get("match_info", [])]
                context_lineups.extend(match_info_snippets)
        else:
            context_lineups = ["ESTADO DE ALINEACIONES: CONFIRMADAS EN VIVO."]
            context_lineups.extend(valid_lineups_snippets)

        stadium_snippets = [res["snippet"] for res in search_results.get("stadium_and_weather", [])]
        weather_grass_snippets = [res["snippet"] for res in search_results.get("realtime_weather_grass", [])]
        
        # Extraer snippets
        context = {
            "match_info": [res["snippet"] for res in search_results.get("match_info", [])],
            "lineups": context_lineups,
            "referee": [res["snippet"] for res in search_results.get("referee", [])],
            "stadium_and_weather": stadium_snippets + weather_grass_snippets,
            "player_rumors": [res["snippet"] for res in search_results.get("player_rumors", [])],
            "scraped_pages": []
        }
        
        # Opcionalmente, leer contenido de las páginas de manera concurrente
        match_search = search_results.get("match_info", [])
        lineups_search = search_results.get("lineups", [])
        referee_search = search_results.get("referee", [])
        
        urls_to_fetch = []
        for l in [match_search, lineups_search, referee_search]:
            if l:
                urls_to_fetch.append(l[0]["url"])
                
        # Limitar a máximo 3 URLs para no abusar
        urls_to_fetch = list(set(urls_to_fetch))[:3]
        
        if urls_to_fetch:
            print(f"[DataCollector] Descargando contenido detallado de {len(urls_to_fetch)} páginas concurrentemente...")
            with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
                fetch_futures = {
                    executor.submit(self.fetch_page_text, url): url 
                    for url in urls_to_fetch
                }
                for future in concurrent.futures.as_completed(fetch_futures):
                    url = fetch_futures[future]
                    try:
                        page_text = future.result()
                        if page_text:
                            context["scraped_pages"].append({
                                "url": url,
                                "content": page_text[:2000]
                            })
                    except Exception as e:
                        print(f"[DataCollector] Error descargando {url}: {e}")
                        
        return context

# Prueba rápida si se ejecuta directamente
if __name__ == "__main__":
    collector = DataCollector()
    data = collector.collect_all_data("Real Madrid", "Barcelona")
    print(json.dumps(data, indent=2, ensure_ascii=False)[:1000])
