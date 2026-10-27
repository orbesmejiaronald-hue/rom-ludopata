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

    def search_duckduckgo(self, query: str, max_results: int = 4):
        """
        Busca en DuckDuckGo usando la librería moderna DDGS. Cero bloqueos y respuesta ultra rápida.
        """
        print(f"[DataCollector] Buscando en internet: '{query}'...")
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
            print(f"[DataCollector] Nota de búsqueda ({e}). Continuando con datos disponibles.")

        return []

    def fetch_page_text(self, url: str) -> str:
        """
        Obtiene el texto legible de una página web para analizarlo.
        """
        try:
            response = requests.get(url, headers=self.headers, timeout=4)
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
        
        # ── INTEGRACIÓN EN VIVO: Consultar LiveDataProvider (ESPN API Oficial en Tiempo Real) ──
        try:
            from live_data_provider import LiveDataProvider
            provider = LiveDataProvider()
            live_match = provider.find_match_by_teams(local_team, visitor_team)
        except Exception as e:
            print(f"[DataCollector] Nota LiveDataProvider: {e}")
            live_match = {}
        
        queries = {
            "flashscore_data": (f"{match_query} futbol flashscore alineaciones", 4),
            "match_info": (f"{match_query} ultimos partidos resultados estadisticas", 4),
            "lineups": (f"{match_query} alineaciones titulares bajas", 4),
            "referee": (f"{match_query} arbitro designado", 3),
            "stadium_weather": (f"{match_query} estadio clima pronostico", 3),
            "player_rumors": (f"{match_query} lesionados noticias bajas", 3)
        }
        
        search_results = {}
        
        print("[DataCollector] Lanzando búsquedas en vivo de alta precisión en Flashscore, SofaScore y UEFA...")
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
                    print(f"[DataCollector] Error en consulta '{key}': {e}")
                    search_results[key] = []

        # Extraer snippets para el dict final
        raw_data = {
            "match_info": [r["snippet"] for r in search_results.get("match_info", []) if r.get("snippet")],
            "lineups": [r["snippet"] for r in search_results.get("lineups", []) if r.get("snippet")],
            "referee": [r["snippet"] for r in search_results.get("referee", []) if r.get("snippet")],
            "stadium_and_weather": [r["snippet"] for r in search_results.get("stadium_weather", []) if r.get("snippet")],
            "player_rumors": [r["snippet"] for r in search_results.get("player_rumors", []) if r.get("snippet")],
            "flashscore_data": [r["snippet"] for r in search_results.get("flashscore_data", []) if r.get("snippet")],
            "alineaciones_oficiales": False,
            "live_match_found": False
        }

        # Inyectar datos oficiales en vivo si se encontraron en ESPN
        if live_match and live_match.get("has_official_lineups"):
            print(f"[DataCollector] ¡Alineaciones oficiales confirmadas inyectadas directamente de ESPN para {local_team} vs {visitor_team}!")
            h_names = [p["name"] for p in live_match.get("home_lineup", [])]
            a_names = [p["name"] for p in live_match.get("away_lineup", [])]
            raw_data["lineups"] = [
                f"{local_team} (Titulares Oficiales): {', '.join(h_names)}",
                f"{visitor_team} (Titulares Oficiales): {', '.join(a_names)}"
            ]
            raw_data["alineaciones_oficiales"] = True
            raw_data["live_match_found"] = True
            if live_match.get("stadium"):
                raw_data["stadium_and_weather"].insert(0, f"Estadio Oficial: {live_match['stadium']}")
            if live_match.get("referee"):
                raw_data["referee"].insert(0, f"Árbitro Oficial: {live_match['referee']}")
            if live_match.get("odds"):
                raw_data["draftkings_odds"] = live_match["odds"]

        # Descargar el texto completo de las páginas más relevantes prioritariamente de Flashscore, SofaScore y FotMob
        urls_to_scrape = []
        for key in ["flashscore_data", "lineups", "referee", "stadium_weather"]:
            for item in search_results.get(key, []):
                url = item.get("url")
                if url and url not in urls_to_scrape:
                    # Priorizar dominios de datos deportivos en vivo
                    if any(domain in url for domain in ["flashscore", "sofascore", "besoccer", "fotmob", "as.com", "marca.com", "uefa.com"]):
                        urls_to_scrape.insert(0, url)
                    else:
                        urls_to_scrape.append(url)
                    if len(urls_to_scrape) >= 5:
                        break
            if len(urls_to_scrape) >= 5:
                break
                
        print(f"[DataCollector] Descargando contenido en vivo de {len(urls_to_scrape)} fuentes de datos clave (Flashscore, SofaScore, UEFA)...")
        scraped_pages = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            future_to_url = {executor.submit(self.fetch_page_text, url): url for url in urls_to_scrape}
            for future in concurrent.futures.as_completed(future_to_url):
                url = future_to_url[future]
                try:
                    text = future.result()
                    if text and len(text) > 100:
                        scraped_pages.append({"url": url, "content": text})
                except Exception as e:
                    print(f"[DataCollector] Error raspando {url}: {e}")
                    
        raw_data["scraped_pages"] = scraped_pages
                    
        # Validar snippets de lineups
        lineups_snippets = raw_data["lineups"]
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
