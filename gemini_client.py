import os
import re
import json

class GeminiClient:
    def __init__(self):
        # Intentar cargar desde un archivo .env de forma manual para evitar dependencias
        base_dir = os.path.dirname(os.path.abspath(__file__))
        env_path = os.path.join(base_dir, ".env")
        if os.path.exists(env_path):
            try:
                with open(env_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            parts = line.split("=", 1)
                            key = parts[0].strip()
                            val = parts[1].strip()
                            if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
                                val = val[1:-1]
                            os.environ[key] = val
            except Exception as e:
                print(f"[GeminiClient] Advertencia al leer archivo .env en {env_path}: {e}")

        self.api_key = os.environ.get("GEMINI_API_KEY")
        self.client = None
        self.client_type = None

        if not self.api_key:
            print("[GeminiClient] ADVERTENCIA: La variable de entorno GEMINI_API_KEY no está configurada.")
            print("[GeminiClient] Entrando en modo de simulación local (MOCK) para evitar errores.")
            self.client_type = "mock"
            return

        # Intentar cargar google-genai (SDK moderno)
        try:
            from google import genai
            # Si se pasa api_key=None o vacío, puede fallar; nos aseguramos
            self.client = genai.Client(api_key=self.api_key)
            self.client_type = "genai"
            print("[GeminiClient] Inicializado usando SDK moderno 'google-genai'.")
        except (ImportError, ValueError, Exception) as e:
            # Intentar cargar google-generativeai (SDK anterior) como fallback
            try:
                import google.generativeai as genai_legacy
                genai_legacy.configure(api_key=self.api_key)
                self.client = genai_legacy
                self.client_type = "generativeai"
                print("[GeminiClient] Inicializado usando SDK clásico 'google-generativeai'.")
            except (ImportError, Exception):
                print(f"[GeminiClient] Error al inicializar clientes de IA ({e}). Usando modo mock.")
                self.client_type = "mock"

    def generate_content(self, prompt: str, system_instruction: str = None) -> str:
        """
        Genera texto usando el modelo Gemini disponible o respuestas simuladas coherentes.
        """
        if self.client_type == "mock":
            return self._get_mock_response(prompt)

        import time
        import random

        candidate_models = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"]
        max_retries = 3
        
        for attempt in range(max_retries):
            for model_name in candidate_models:
                try:
                    if self.client_type == "genai":
                        from google.genai import types
                        config = types.GenerateContentConfig()
                        if system_instruction:
                            config.system_instruction = system_instruction
                        
                        response = self.client.models.generate_content(
                            model=model_name,
                            contents=prompt,
                            config=config
                        )
                        if response and response.text:
                            return response.text
                    elif self.client_type == "generativeai":
                        if system_instruction:
                            model = self.client.GenerativeModel(
                                model_name=model_name,
                                system_instruction=system_instruction
                            )
                        else:
                            model = self.client.GenerativeModel(model_name=model_name)

                        response = model.generate_content(prompt)
                        if response and response.text:
                            return response.text
                except Exception as inner_e:
                    print(f"[GeminiClient] Error con modelo '{model_name}' (intento {attempt+1}): {inner_e}")
                    time.sleep(0.5)

            wait_time = (2 ** attempt) + random.random()
            print(f"[GeminiClient] Error general llamando a Gemini (intento {attempt+1}/{max_retries}). Esperando {wait_time:.2f}s antes de reintentar...")
            if attempt == max_retries - 1:
                print(f"[GeminiClient] Se agotaron los reintentos para la llamada a Gemini. Usando mock de emergencia.")
                return self._get_mock_response(prompt)
            time.sleep(wait_time)

    def generate_content_stream(self, prompt: str, system_instruction: str = None):
        """
        Generador para transmitir la respuesta de Gemini en tiempo real (streaming).
        """
        if self.client_type == "mock":
            response_text = self._get_mock_response(prompt)
            if response_text == "{}":
                response_text = "Modo SIMULADO activo: No se detectó la variable de entorno `GEMINI_API_KEY`. Para consultas en tiempo real y análisis reales, configura tu clave API de Gemini. Como tu asistente deportivo ROM LUDOPATA 1.2 estoy listo para ayudarte."
            
            import time
            words = response_text.split(" ")
            for i, word in enumerate(words):
                yield word + (" " if i < len(words) - 1 else "")
                time.sleep(0.02)
            return

        import time
        import random
        candidate_models = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"]
        max_retries = 3
        
        for attempt in range(max_retries):
            for model_name in candidate_models:
                try:
                    if self.client_type == "genai":
                        from google.genai import types
                        config = types.GenerateContentConfig()
                        if system_instruction:
                            config.system_instruction = system_instruction
                        
                        response = self.client.models.generate_content_stream(
                            model=model_name,
                            contents=prompt,
                            config=config
                        )
                        chunk_emitted = False
                        for chunk in response:
                            if chunk.text:
                                yield chunk.text
                                chunk_emitted = True
                        if chunk_emitted:
                            return
                    elif self.client_type == "generativeai":
                        if system_instruction:
                            model = self.client.GenerativeModel(
                                model_name=model_name,
                                system_instruction=system_instruction
                            )
                        else:
                            model = self.client.GenerativeModel(model_name=model_name)

                        response = model.generate_content(prompt, stream=True)
                        chunk_emitted = False
                        for chunk in response:
                            if chunk.text:
                                yield chunk.text
                                chunk_emitted = True
                        if chunk_emitted:
                            return
                except Exception as inner_e:
                    print(f"[GeminiClient] Error stream con modelo '{model_name}' (intento {attempt+1}): {inner_e}")
                    time.sleep(0.5)

            wait_time = (2 ** attempt) + random.random()
            print(f"[GeminiClient] Error general llamando a Gemini Stream (intento {attempt+1}/{max_retries}). Esperando {wait_time:.2f}s antes de reintentar...")
            if attempt == max_retries - 1:
                print(f"[GeminiClient] Se agotaron los reintentos para la llamada a Gemini Stream. Usando mock.")
                words = "Error al conectar con la API de Gemini. Por favor, verifica tu conexión o tu API Key.".split(" ")
                for word in words:
                    yield word + " "
                return
            time.sleep(wait_time)

    def _get_mock_response(self, prompt: str) -> str:
        """
        Genera respuestas simuladas JSON válidas para que la UI funcione sin API key.
        """
        import unicodedata
        import json
        import re
        
        # 0. Caso Perfilación de Jugadores
        if "lista de jugadores" in prompt or ("rating_ofensivo" in prompt and "posicion" in prompt):
            players_list = []
            match = re.search(r'\[\s*".*?"\s*\]', prompt, re.DOTALL)
            if match:
                try:
                    players_list = json.loads(match.group(0))
                except:
                    pass
            if not players_list:
                players_list = re.findall(r'"([^"]+)"', prompt)
                players_list = [p for p in players_list if p not in ["Nombre Jugador 1", "Nombre Jugador 2", "posicion", "rating_ofensivo", "rating_defensivo", "DEF", "ATT", "GK", "MID"]]

            player_db = {
                "vini jr": ("ATT", 2.5, 1.2),
                "mbappe": ("ATT", 2.6, 1.3),
                "bellingham": ("MID", 2.2, 0.6),
                "rodrygo": ("ATT", 1.8, 1.0),
                "valverde": ("MID", 1.6, 0.5),
                "lewandowski": ("ATT", 2.1, 1.2),
                "lamine yamal": ("ATT", 2.3, 1.1),
                "raphinha": ("ATT", 1.7, 0.9),
                "pedri": ("MID", 1.8, 0.7),
                "gavi": ("MID", 1.4, 0.6),
                "courtois": ("GK", 0.05, 0.3),
                "ter stegen": ("GK", 0.05, 0.4),
                "rudiger": ("DEF", 0.3, 0.4),
                "militao": ("DEF", 0.4, 0.5),
                "carvajal": ("DEF", 0.6, 0.5),
                "kounde": ("DEF", 0.5, 0.5),
                "araujo": ("DEF", 0.3, 0.4),
                "lunin": ("GK", 0.05, 0.8),
                "lucas vazquez": ("DEF", 0.9, 1.1),
                "vallejo": ("DEF", 0.3, 1.6),
                "fran garcia": ("DEF", 0.8, 1.1),
                "ceballos": ("MID", 0.9, 1.1),
                "modric": ("MID", 1.1, 1.2),
                "arda guler": ("MID", 1.3, 1.2),
                "endrick": ("ATT", 1.4, 1.2),
                "brahim diaz": ("ATT", 1.5, 1.1),
                "nico paz": ("MID", 1.0, 1.1),
                "jacobo ramon": ("DEF", 0.4, 1.3)
            }
            
            response_dict = {}
            for p in players_list:
                p_norm = ''.join(c for c in unicodedata.normalize('NFD', p.lower()) if unicodedata.category(c) != 'Mn')
                p_norm = re.sub(r'[^\w\s]', '', p_norm).strip()
                
                pos, r_att, r_def = "MID", 1.0, 1.0
                found = False
                for db_name, stats in player_db.items():
                    if db_name in p_norm or p_norm in db_name:
                        pos, r_att, r_def = stats
                        found = True
                        break
                if not found:
                    if any(w in p_norm for w in ["gk", "portero", "arquero"]):
                        pos, r_att, r_def = "GK", 0.05, 1.0
                    elif any(w in p_norm for w in ["def", "back", "zaguero", "lateral"]):
                        pos, r_att, r_def = "DEF", 0.5, 1.0
                    elif any(w in p_norm for w in ["att", "forward", "delantero", "goleador"]):
                        pos, r_att, r_def = "ATT", 1.5, 1.0
                
                response_dict[p] = {
                    "posicion": pos,
                    "rating_ofensivo": r_att,
                    "rating_defensivo": r_def
                }
            return json.dumps(response_dict, ensure_ascii=False)

        # 1. Caso Análisis Táctico
        if "formación probable" in prompt or "TacticalAnalyzer" in prompt or "alineaciones" in prompt:
            # Obtener nombres de equipos
            match_local = re.search(r"Local:\s*([^\n]+)", prompt)
            match_visitor = re.search(r"Visitante:\s*([^\n]+)", prompt)
            local = match_local.group(1).strip() if match_local else "Local"
            visitor = match_visitor.group(1).strip() if match_visitor else "Visitante"
            
            def get_hash_val(name1, name2):
                return sum(ord(c) for c in (name1 + name2))
            hash_val = get_hash_val(local, visitor)
            
            formations = ["4-3-3", "4-2-3-1", "3-5-2", "4-4-2", "5-3-2"]
            form_l = formations[hash_val % len(formations)]
            form_v = formations[(hash_val + 2) % len(formations)]
            
            styles = [
                "Posesión paciente, presión alta tras pérdida y desborde por bandas.",
                "Defensa en bloque medio, transiciones veloces y contraataques por el centro.",
                "Bloque bajo defensivo muy compacto y pelotazos largos para el delantero centro.",
                "Presión asfixiante en campo contrario, ritmo de juego vertiginoso y transiciones directas.",
                "Estructura sólida de tres centrales, control de los carrileros y ataque posicional."
            ]
            style_l = styles[hash_val % len(styles)]
            style_v = styles[(hash_val + 3) % len(styles)]
            
            is_official = True
            warning_msg = ""
            if "NO CONFIRMADAS" in prompt or "No confirmada" in prompt or "NO CONFIRMADAS EN VIVO" in prompt:
                is_official = False
                warning_msg = "⚠️ ADVERTENCIA: Alineaciones oficiales no confirmadas en vivo. Basado en el último partido de cada equipo."
                
            return json.dumps({
                "local_formacion": form_l,
                "local_estilo": style_l,
                "visitante_formacion": form_v,
                "visitante_estilo": style_v,
                "analisis_enfrentamiento": f"El parado táctico de {local} intentará dominar la posesión de balón. Sin embargo, {visitor} representa un peligro latente en transiciones rápidas.",
                "zonas_clave": "El control del mediocampo y las coberturas defensivas de los laterales.",
                "ventaja_tactica": f"El equipo {local if hash_val % 2 == 0 else visitor} tiene una ligera ventaja táctica debido a su versatilidad táctica.",
                "alineaciones_oficiales": is_official,
                "advertencia_lineas": warning_msg
            }, ensure_ascii=False)

        # 5. Caso Extracción de Parámetros Estadísticos
        if "variables cuantitativas" in prompt or "local_expected_goals" in prompt:
            local_match = re.search(r"Local:\s*([^\n]+)", prompt)
            visitor_match = re.search(r"Visitante:\s*([^\n]+)", prompt)
            local = local_match.group(1).strip() if local_match else "Local"
            visitor = visitor_match.group(1).strip() if visitor_match else "Visitante"
            
            def get_hash_val(name1, name2):
                return sum(ord(c) for c in (name1 + name2))
            hash_val = get_hash_val(local, visitor)
            
            # Determinar si es neutral
            is_neutral = any(kw in prompt.lower() for kw in ["mundial", "world cup", "copa del mundo", "neutral"])
            
            base_l = 1.35 + (hash_val % 6) * 0.15 # 1.35 a 2.10
            base_v = 1.05 + ((hash_val // 6) % 5) * 0.15 # 1.05 a 1.65
            
            if is_neutral:
                mean_goals = (base_l + base_v) / 2
                l_goals = round(mean_goals, 2)
                v_goals = round(mean_goals * 0.95, 2)
            else:
                l_goals = round(base_l, 2)
                v_goals = round(base_v, 2)
                
            l_corners = round(4.5 + (hash_val % 5) * 0.5, 1)
            v_corners = round(3.5 + ((hash_val // 5) % 5) * 0.5, 1)
            expected_cards = round(3.5 + ((hash_val // 2) % 6) * 0.5, 1)
            
            return json.dumps({
                "local_expected_goals": l_goals,
                "visitor_expected_goals": v_goals,
                "local_expected_corners": l_corners,
                "visitor_expected_corners": v_corners,
                "expected_cards": expected_cards
            }, ensure_ascii=False)

        # 2. Caso Validación Lógica de Simulación
        if "Analiza la siguiente simulación de un partido" in prompt or "inspector de consistencia deportiva" in prompt:
            return json.dumps({
                "es_valido": True,
                "motivo_rechazo": ""
            }, ensure_ascii=False)

        # 3. Caso Simulación de Partido
        if "Simula el partido" in prompt or "simulacion_id" in prompt:
            # Obtener nombres de equipos
            match_local = re.search(r"Local:\s*([^\n]+)", prompt)
            match_visitor = re.search(r"Visitante:\s*([^\n]+)", prompt)
            local = match_local.group(1).strip() if match_local else "Local"
            visitor = match_visitor.group(1).strip() if match_visitor else "Visitante"
            
            # Obtener ID de la simulación
            match_id = re.search(r"Simulación (\d+)", prompt)
            sim_id = int(match_id.group(1)) if match_id else 1
            
            # Obtener goles esperados
            local_exp_match = re.search(r"Goles locales esperados:\s*(\d+(?:\.\d+)?)", prompt)
            visitor_exp_match = re.search(r"Goles visitantes esperados:\s*(\d+(?:\.\d+)?)", prompt)
            
            l_lambda = float(local_exp_match.group(1)) if local_exp_match else 1.5
            v_lambda = float(visitor_exp_match.group(1)) if visitor_exp_match else 1.2
            
            def get_hash_val(name1, name2):
                return sum(ord(c) for c in (name1 + name2))
            hash_val = get_hash_val(local, visitor) + sim_id
            
            goles_l = hash_val % (int(l_lambda) + 2)
            goles_v = (hash_val // 2) % (int(v_lambda) + 2)
            
            anotadores = []
            for g in range(goles_l):
                anotadores.append({
                    "minuto": 10 + (hash_val * (g+1)) % 75,
                    "jugador": f"Goleador L{g+1}",
                    "equipo": "local"
                })
            for g in range(goles_v):
                anotadores.append({
                    "minuto": 15 + (hash_val * (g+4)) % 75,
                    "jugador": f"Goleador V{g+1}",
                    "equipo": "visitante"
                })
                
            anotadores.sort(key=lambda x: x["minuto"])
            
            cronica = [
                f"Minuto 1: Pitazo inicial en el estadio, rueda el balón en el enfrentamiento entre {local} y {visitor}.",
            ]
            for a in anotadores:
                cronica.append(f"Minuto {a['minuto']}: ¡GOOOOOL! {a['jugador']} anota con gran definición para el equipo {a['equipo']}.")
            cronica.append(f"Minuto 90: Final del encuentro con marcador de {local} {goles_l} - {goles_v} {visitor}.")
            
            return json.dumps({
                "simulacion_id": sim_id,
                "escenario": f"Escenario {sim_id}",
                "goles_local": goles_l,
                "goles_visitante": goles_v,
                "anotadores": anotadores,
                "tarjetas_amarillas": [
                    {"minuto": 30 + (hash_val % 45), "jugador": "Defensor L", "equipo": "local"},
                    {"minuto": 45 + ((hash_val // 2) % 40), "jugador": "Mediocampista V", "equipo": "visitante"}
                ],
                "tarjetas_rojas": [],
                "tiros_esquina_local": round(l_lambda * 3.5),
                "tiros_esquina_visitante": round(v_lambda * 3.0),
                "posesion_local_porcentaje": 45 + (hash_val % 15),
                "cronica_minuto_a_minuto": cronica
            }, ensure_ascii=False)

        # 4. Caso Analizador de Mercado
        if "Investiga y estima las cuotas" in prompt or "MarketAnalyzer" in prompt or "apostador profesional" in prompt or "sharp bettor" in prompt:
            local_pct_match = re.search(r"Victoria Local:\s*(\d+(?:\.\d+)?)%", prompt)
            draw_pct_match = re.search(r"Empate:\s*(\d+(?:\.\d+)?)%", prompt)
            visitor_pct_match = re.search(r"Victoria Visitante:\s*(\d+(?:\.\d+)?)%", prompt)
            
            pLoc = float(local_pct_match.group(1)) if local_pct_match else 45.0
            pDra = float(draw_pct_match.group(1)) if draw_pct_match else 25.0
            pVis = float(visitor_pct_match.group(1)) if visitor_pct_match else 30.0
            
            cLoc_fair = round(100 / pLoc, 2) if pLoc > 0 else 3.00
            cDra_fair = round(100 / pDra, 2) if pDra > 0 else 3.50
            cVis_fair = round(100 / pVis, 2) if pVis > 0 else 3.30
            
            cLoc = round(cLoc_fair * 0.93, 2)
            cDra = round(cDra_fair * 0.94, 2)
            cVis = round(cVis_fair * 0.93, 2)
            
            local_match = re.search(r"Local:\s*([^\n]+)", prompt)
            visitor_match = re.search(r"Visitante:\s*([^\n]+)", prompt)
            local = local_match.group(1).strip() if local_match else "Local"
            visitor = visitor_match.group(1).strip() if visitor_match else "Visitante"
            
            if pLoc > 48.0:
                rec = f"Victoria de {local} (Hándicap Asiático -0.5) con stake moderado."
                h_line = f"{local} -0.5"
                h_odds = cLoc
            elif pVis > 38.0:
                rec = f"Hándicap Asiático {visitor} +0.5 o doble oportunidad visitante."
                h_line = f"{visitor} +0.5"
                h_odds = round(cVis * 0.85, 2)
            else:
                rec = "Menos de 2.5 goles totales o Empate en el mercado de cuotas."
                h_line = "Hándicap Asiático 0.0"
                h_odds = 1.90
                
            return json.dumps({
                "cuota_local_estimada": cLoc,
                "cuota_empate_estimada": cDra,
                "cuota_visitante_estimada": cVis,
                "handicap_asiatico_linea": h_line,
                "handicap_asiatico_cuota": h_odds,
                "cuota_over_2_5_estimada": 1.95,
                "cuota_under_2_5_estimada": 1.85,
                "cuota_over_9_5_corners_estimada": 1.80,
                "cuota_under_9_5_corners_estimada": 1.90,
                "cuota_over_4_5_tarjetas_estimada": 1.85,
                "cuota_under_4_5_tarjetas_estimada": 1.85,
                "comparativa_valor": [
                    f"El mercado estima a {local} con cuota {cLoc}, lo que representa valor según nuestro modelo de Poisson ({pLoc:.1f}% prob).",
                    "El mercado de corners se observa equilibrado con las estimaciones del árbitro designado."
                ],
                "recomendacion_apuesta": rec
            }, ensure_ascii=False)

        # Caso Detalles del Entorno (Estadio, Clima, Árbitro)
        if "entorno del partido" in prompt or "estadio_nombre" in prompt:
            local_match = re.search(r"Local:\s*([^\n]+)", prompt)
            visitor_match = re.search(r"Visitante:\s*([^\n]+)", prompt)
            local = local_match.group(1).strip() if local_match else "Local"
            visitor = visitor_match.group(1).strip() if visitor_match else "Visitante"
            
            def get_hash_val(name1, name2):
                return sum(ord(c) for c in (name1 + name2))
            hash_val = get_hash_val(local, visitor)
            
            referees = [
                {"name": "Jesús Gil Manzano", "cards": "5.3 amarillas, 0.2 rojas", "style": "Riguroso y dialoga poco, saca tarjetas rápido.", "strict": "Sí"},
                {"name": "César Arturo Ramos", "cards": "4.1 amarillas, 0.1 rojas", "style": "De libre fluidez, pita solo contactos claros.", "strict": "No"},
                {"name": "Wilmar Roldán", "cards": "6.2 amarillas, 0.4 rojas", "style": "Estilo riguroso, saca tarjetas rápido ante protestas.", "strict": "Sí"},
                {"name": "Szymon Marciniak", "cards": "3.8 amarillas, 0.1 rojas", "style": "Control calmado del temperamento, deja jugar.", "strict": "No"},
                {"name": "Michael Oliver", "cards": "4.4 amarillas, 0.2 rojas", "style": "Permisivo con el contacto físico, castiga la reiteración.", "strict": "No"}
            ]
            ref = referees[hash_val % len(referees)]
            
            # Detectar si es neutral (Mundial)
            is_neutral = any(kw in prompt.lower() for kw in ["mundial", "world cup", "copa del mundo", "neutral"])
            
            if is_neutral:
                stadiums = [
                    {"name": "Estadio Olímpico de Berlín", "cap": "74,475", "grass": "Natural", "impact": "Cancha neutral (Eurocopa / Torneo Europeo). Sin ventaja de localía clásica."},
                    {"name": "Estadio de Lusail", "cap": "88,966", "grass": "Natural", "impact": "Cancha neutral en Qatar (Copa del Mundo). Césped refrigerado, sin ventaja de localía."},
                    {"name": "MetLife Stadium", "cap": "82,500", "grass": "Híbrido", "impact": "Cancha neutral en EE.UU. (Copa América / Mundial). Sin ventaja de localía clásica."}
                ]
                stadium = stadiums[hash_val % len(stadiums)]
            else:
                stadium = {
                    "name": f"Estadio del {local}",
                    "cap": f"{35000 + (hash_val % 8) * 7000:,} espectadores",
                    "grass": "Natural" if (hash_val % 2 == 0) else "Híbrido",
                    "impact": f"Fuerte localía. La afición de {local} ejerce presión y genera un ambiente hostil para el visitante."
                }
                
            climates = ["Despejado, 22°C, humedad 45%", "Lluvia ligera, 16°C, césped rápido", "Nublado, 19°C, viento moderado", "Soleado, 28°C, calor seco"]
            weather = climates[hash_val % len(climates)]
            
            return json.dumps({
                "estadio_nombre": stadium["name"],
                "estadio_capacidad": stadium["cap"],
                "estadio_cesped": stadium["grass"],
                "estadio_localia_impacto": stadium["impact"],
                "clima_pronostico": weather,
                "arbitro_nombre": ref["name"],
                "arbitro_promedio_tarjetas": ref["cards"],
                "arbitro_tarjetero": ref["strict"],
                "arbitro_estilo": ref["style"]
            }, ensure_ascii=False)

        # Fallback genérico de JSON
        return "{}"
