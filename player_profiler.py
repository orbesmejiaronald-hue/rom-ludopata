import json
import os
import re
import unicodedata

class PlayerProfiler:
    def __init__(self, gemini_client):
        self.client = gemini_client
        self.cache_path = "player_profiles.json"
        self.profiles = {}
        self.load_cache()

    def load_cache(self):
        if os.path.exists(self.cache_path):
            try:
                with open(self.cache_path, "r", encoding="utf-8") as f:
                    self.profiles = json.load(f)
            except Exception as e:
                print(f"[PlayerProfiler] Error leyendo caché: {e}. Inicializando vacío.")
                self.profiles = {}

    def save_cache(self):
        try:
            with open(self.cache_path, "w", encoding="utf-8") as f:
                json.dump(self.profiles, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[PlayerProfiler] Error guardando caché: {e}")

    def normalize_name(self, name: str) -> str:
        if not name:
            return ""
        s = name.lower().strip()
        # Eliminar acentos
        s = ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')
        # Eliminar puntuaciones
        s = re.sub(r'[^\w\s]', '', s)
        # Espacios múltiples a uno
        s = re.sub(r'\s+', ' ', s).strip()
        return s

    def profile_missing_players(self, players: list, team_name: str):
        """
        Consulta Gemini para perfilar de golpe todos los jugadores que falten en la caché.
        """
        missing_players = []
        normalized_map = {}
        
        for p in players:
            norm_p = self.normalize_name(p)
            if not norm_p:
                continue
            normalized_map[norm_p] = p
            if norm_p not in self.profiles:
                missing_players.append(p)
                
        if not missing_players:
            return
            
        print(f"[PlayerProfiler] Consultando perfiles para {len(missing_players)} jugadores de '{team_name}'...")
        
        prompt = f"""
Analiza la siguiente lista de jugadores del equipo '{team_name}':
{json.dumps(missing_players, ensure_ascii=False)}

Para cada jugador en la lista, estima:
1. "posicion": Su posición principal en el campo, clasificada estrictamente en una de estas: "GK" (portero), "DEF" (defensor), "MID" (mediocampista), "ATT" (delantero).
2. "rating_ofensivo": Su peso ofensivo relativo al promedio de la plantilla de su propio equipo (rango: 0.1 a 3.0, donde 1.0 representa el nivel promedio de la plantilla de este equipo).
3. "rating_defensivo": Su debilidad defensiva relativa al promedio de la plantilla de su propio equipo (rango: 0.1 a 3.0, donde 1.0 representa el nivel promedio de la plantilla de este equipo; un valor inferior a 1.0 indica que es más sólido defensivamente que su promedio y un valor superior indica mayor debilidad).

Devuelve tu respuesta únicamente en un formato JSON estructurado como este, mapeando el nombre del jugador a su perfil (sin bloques markdown adicionales):
{{
  "Nombre Jugador 1": {{
    "posicion": "DEF",
    "rating_ofensivo": 0.50,
    "rating_defensivo": 0.40
  }},
  "Nombre Jugador 2": {{
    "posicion": "ATT",
    "rating_ofensivo": 2.10,
    "rating_defensivo": 1.20
  }}
}}
"""
        system_instruction = "Eres un analista de datos cuantitativos de fútbol profesional de nivel élite. Devuelve exclusivamente el JSON solicitado en español."
        
        try:
            raw_response = self.client.generate_content(prompt, system_instruction=system_instruction)
            clean_response = raw_response.strip()
            if clean_response.startswith("```"):
                lines = clean_response.splitlines()
                if lines[0].startswith("```json") or lines[0].startswith("```"):
                    clean_response = "\n".join(lines[1:-1])
                    
            profiles_batch = json.loads(clean_response)
            
            for raw_name, profile in profiles_batch.items():
                norm_name = self.normalize_name(raw_name)
                self.profiles[norm_name] = {
                    "nombre_original": raw_name,
                    "posicion": profile.get("posicion", "MID"),
                    "rating_ofensivo": float(profile.get("rating_ofensivo", 1.0)),
                    "rating_defensivo": float(profile.get("rating_defensivo", 1.0))
                }
                
            # Forzar fallback si algún jugador no se devolvió en el JSON
            for p in missing_players:
                norm_p = self.normalize_name(p)
                if norm_p not in self.profiles:
                    self.profiles[norm_p] = {
                        "nombre_original": p,
                        "posicion": "MID",
                        "rating_ofensivo": 1.0,
                        "rating_defensivo": 1.0
                    }
                    
            self.save_cache()
        except Exception as e:
            print(f"[PlayerProfiler] Error perfilando jugadores: {e}. Usando fallbacks por defecto.")
            for p in missing_players:
                norm_p = self.normalize_name(p)
                self.profiles[norm_p] = {
                    "nombre_original": p,
                    "posicion": "MID",
                    "rating_ofensivo": 1.0,
                    "rating_defensivo": 1.0
                }
            self.save_cache()

    def get_player_profile(self, name: str) -> dict:
        norm_name = self.normalize_name(name)
        return self.profiles.get(norm_name, {
            "nombre_original": name,
            "posicion": "MID",
            "rating_ofensivo": 1.0,
            "rating_defensivo": 1.0
        })
