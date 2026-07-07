import json
import re

class SimulationList(list):
    """
    Subclase de lista para encapsular las crónicas de las 10 simulaciones
    y adjuntar las estadísticas cuantitativas del modelo de Monte Carlo.
    """
    def __init__(self, iterable, monte_carlo=None):
        super().__init__(iterable)
        self.monte_carlo = monte_carlo

class SimulationEngine:
    def __init__(self, gemini_client):
        self.client = gemini_client

    def _extract_statistical_parameters(self, local: str, visitor: str, data: dict) -> dict:
        """
        Extrae lambdas y medias estadísticas de los datos recopilados usando el LLM.
        """
        print(f"[SimulationEngine] Extrayendo parámetros estadísticos cuantitativos para {local} vs {visitor}...")
        referee_info = "\n".join(data.get("referee", []))
        weather_info = "\n".join(data.get("stadium_and_weather", []))
        rumors_info = "\n".join(data.get("player_rumors", []))
        match_info = "\n".join(data.get("match_info", []))
        
        scraped_content = ""
        for page in data.get("scraped_pages", []):
            scraped_content += f"\n--- Contenido de la página {page['url']} ---\n{page['content']}\n"
            
        prompt = f"""
Analiza la siguiente información de internet para el partido:
Local: {local}
Visitante: {visitor}

Estadísticas y partidos recientes:
{match_info}
Datos del árbitro: {referee_info}
Clima y estadio: {weather_info}
Noticias y rumores: {rumors_info}
{scraped_content}

Tu tarea es estimar y extraer las siguientes variables cuantitativas de rendimiento esperado para ambos equipos:
1. "local_expected_goals" (Lambda local): Goles promedio esperados para el local (rango realista: 0.5 a 4.0).
2. "visitor_expected_goals" (Lambda visitante): Goles promedio esperados para el visitante (rango realista: 0.5 a 4.0).
3. "local_expected_corners": Promedio de corners a favor del local (rango: 2.0 a 10.0).
4. "visitor_expected_corners": Promedio de corners a favor del visitante (rango: 2.0 a 10.0).
5. "expected_cards": Promedio de tarjetas totales sumadas en el partido (amarillas + rojas de ambos, rango: 1.0 a 8.0).
6. "expected_fouls": Promedio de faltas totales sumadas en el partido por ambos equipos (rango: 15.0 a 35.0).

Devuelve tu respuesta únicamente en un formato JSON estructurado como este (sin bloques markdown ```json adicionales, solo el texto JSON puro para json.loads):
{{
  "local_expected_goals": 1.65,
  "visitor_expected_goals": 1.20,
  "local_expected_corners": 5.5,
  "visitor_expected_corners": 4.0,
  "expected_cards": 4.5,
  "expected_fouls": 24.5
}}
"""
        system_instruction = "Eres un analista de datos cuantitativos deportivos de nivel profesional. Extrae exclusivamente las variables estadísticas y responde con el JSON puro solicitado en español."
        raw_response = self.client.generate_content(prompt, system_instruction=system_instruction)
        
        clean_response = raw_response.strip()
        if clean_response.startswith("```"):
            lines = clean_response.splitlines()
            if lines[0].startswith("```json") or lines[0].startswith("```"):
                clean_response = "\n".join(lines[1:-1])
                
        try:
            return json.loads(clean_response)
        except Exception as e:
            print(f"[SimulationEngine] Error parseando parámetros estadísticos: {e}. Usando fallbacks realistas.")
            return {
                "local_expected_goals": 1.5,
                "visitor_expected_goals": 1.2,
                "local_expected_corners": 5.0,
                "visitor_expected_corners": 4.0,
                "expected_cards": 4.0,
                "expected_fouls": 24.0
            }

    def _run_monte_carlo_simulation(self, local_lambda: float, visitor_lambda: float, 
                                    local_corners_mean: float, visitor_corners_mean: float, 
                                    cards_mean: float, fouls_mean: float = 24.0) -> dict:
        """
        Ejecuta 10,000 simulaciones de Poisson en Python para obtener probabilidades de apuestas precisas.
        """
        import math
        import random
        
        simulations_count = 10000
        
        local_wins = 0
        draws = 0
        visitor_wins = 0
        
        over_1_5 = 0
        over_2_5 = 0
        over_3_5 = 0
        
        over_8_5_corners = 0
        over_9_5_corners = 0
        over_10_5_corners = 0
        
        over_3_5_cards = 0
        over_4_5_cards = 0
        over_5_5_cards = 0

        over_21_5_fouls = 0
        over_25_5_fouls = 0
        over_29_5_fouls = 0
        
        total_goles_local = 0
        total_goles_visitante = 0
        total_corners_local = 0
        total_corners_visitor = 0
        total_cards = 0
        total_fouls = 0
        
        # Poisson helper
        def poisson_random(lmbda):
            L = math.exp(-lmbda)
            k = 0
            p = 1.0
            while p > L:
                k += 1
                p *= random.random()
            return k - 1

        for _ in range(simulations_count):
            g_l = max(0, poisson_random(local_lambda))
            g_v = max(0, poisson_random(visitor_lambda))
            
            total_goles_local += g_l
            total_goles_visitante += g_v
            
            # 1X2
            if g_l > g_v:
                local_wins += 1
            elif g_l == g_v:
                draws += 1
            else:
                visitor_wins += 1
                
            # Over/Under Goles
            total_goals = g_l + g_v
            if total_goals > 1.5:
                over_1_5 += 1
            if total_goals > 2.5:
                over_2_5 += 1
            if total_goals > 3.5:
                over_3_5 += 1
                
            # Corners, Tarjetas y Faltas
            c_l = max(0, poisson_random(local_corners_mean))
            c_v = max(0, poisson_random(visitor_corners_mean))
            cards = max(0, poisson_random(cards_mean))
            fouls = max(0, poisson_random(fouls_mean))
            
            total_corners_local += c_l
            total_corners_visitor += c_v
            total_cards += cards
            total_fouls += fouls
            
            total_corners = c_l + c_v
            if total_corners > 8.5:
                over_8_5_corners += 1
            if total_corners > 9.5:
                over_9_5_corners += 1
            if total_corners > 10.5:
                over_10_5_corners += 1
                
            if cards > 3.5:
                over_3_5_cards += 1
            if cards > 4.5:
                over_4_5_cards += 1
            if cards > 5.5:
                over_5_5_cards += 1

            if fouls > 21.5:
                over_21_5_fouls += 1
            if fouls > 25.5:
                over_25_5_fouls += 1
            if fouls > 29.5:
                over_29_5_fouls += 1
            
        return {
            "probabilidad_victoria_local": (local_wins / simulations_count) * 100,
            "probabilidad_empate": (draws / simulations_count) * 100,
            "probabilidad_victoria_visitante": (visitor_wins / simulations_count) * 100,
            "probabilidad_over_1_5": (over_1_5 / simulations_count) * 100,
            "probabilidad_over_2_5": (over_2_5 / simulations_count) * 100,
            "probabilidad_over_3_5": (over_3_5 / simulations_count) * 100,
            "probabilidad_over_8_5_corners": (over_8_5_corners / simulations_count) * 100,
            "probabilidad_over_9_5_corners": (over_9_5_corners / simulations_count) * 100,
            "probabilidad_over_10_5_corners": (over_10_5_corners / simulations_count) * 100,
            "probabilidad_over_3_5_cards": (over_3_5_cards / simulations_count) * 100,
            "probabilidad_over_4_5_cards": (over_4_5_cards / simulations_count) * 100,
            "probabilidad_over_5_5_cards": (over_5_5_cards / simulations_count) * 100,
            "probabilidad_over_21_5_faltas": (over_21_5_fouls / simulations_count) * 100,
            "probabilidad_over_25_5_faltas": (over_25_5_fouls / simulations_count) * 100,
            "probabilidad_over_29_5_faltas": (over_29_5_fouls / simulations_count) * 100,
            "promedio_goles_local": total_goles_local / simulations_count,
            "promedio_goles_visitante": total_goles_visitante / simulations_count,
            "promedio_corners_local": total_corners_local / simulations_count,
            "promedio_corners_visitante": total_corners_visitor / simulations_count,
            "promedio_tarjetas": total_cards / simulations_count,
            "promedio_faltas": total_fouls / simulations_count
        }

    def _calculate_lineup_adjustment(self, local_team: str, visitor_team: str, lineups_data: list) -> dict:
        """
        Extrae los jugadores, perfila sus ratings y calcula los factores de ajuste F_ataque y F_defensa
        para ambos equipos.
        """
        import unicodedata
        import re
        from player_profiler import PlayerProfiler
        
        profiler = PlayerProfiler(self.client)
        
        def clean_text(t):
            return ''.join(c for c in unicodedata.normalize('NFD', t.lower()) if unicodedata.category(c) != 'Mn')
            
        def extract_players(team_name):
            from dixon_coles import DixonColesModel
            dc = DixonColesModel()
            team_norm = dc.normalize_team(team_name)
            
            line_to_parse = ""
            for line in lineups_data:
                header = line.split(":", 1)[0] if ":" in line else line
                header_norm = dc.normalize_team(header)
                if team_norm in header_norm:
                    line_to_parse = line
                    break
            if not line_to_parse:
                return []
            if ":" in line_to_parse:
                line_to_parse = line_to_parse.split(":", 1)[1]
            
            line_to_parse = re.sub(r'\(gk\)|\(c\)|\bgk\b|\bc\b', '', line_to_parse, flags=re.IGNORECASE)
            line_to_parse = line_to_parse.replace(";", ",").replace(".", ",")
            raw_players = line_to_parse.split(",")
            players = []
            for p in raw_players:
                p_clean = p.strip()
                if len(p_clean) > 3 and not p_clean.isdigit():
                    players.append(p_clean)
            return players

        local_players = extract_players(local_team)
        visitor_players = extract_players(visitor_team)
        
        if local_players:
            profiler.profile_missing_players(local_players, local_team)
        if visitor_players:
            profiler.profile_missing_players(visitor_players, visitor_team)
            
        weights_att = {"ATT": 1.0, "MID": 0.75, "DEF": 0.20, "GK": 0.05}
        weights_def = {"GK": 1.0, "DEF": 1.0, "MID": 0.50, "ATT": 0.10}
        
        def calculate_factors(players):
            if not players:
                return 1.0, 1.0
                
            sum_att = 0.0
            sum_def = 0.0
            w_att_total = 0.0
            w_def_total = 0.0
            
            for p in players:
                prof = profiler.get_player_profile(p)
                pos = prof.get("posicion", "MID")
                r_att = prof.get("rating_ofensivo", 1.0)
                r_def = prof.get("rating_defensivo", 1.0)
                
                w_att = weights_att.get(pos, 0.7)
                w_def = weights_def.get(pos, 0.5)
                
                sum_att += w_att * r_att
                sum_def += w_def * r_def
                w_att_total += w_att
                w_def_total += w_def
                
            f_att = sum_att / w_att_total if w_att_total > 0 else 1.0
            f_def = sum_def / w_def_total if w_def_total > 0 else 1.0
            return f_att, f_def

        f_att_local, f_def_local = calculate_factors(local_players)
        f_att_visitor, f_def_visitor = calculate_factors(visitor_players)
        
        return {
            "local_players_count": len(local_players),
            "visitor_players_count": len(visitor_players),
            "f_attack_local": f_att_local,
            "f_defense_local": f_def_local,
            "f_attack_visitor": f_att_visitor,
            "f_defense_visitor": f_def_visitor
        }

    def run_all_simulations(self, local_team: str, visitor_team: str, data_context: dict, tactical_analysis: dict) -> list:
        """
        Ejecuta 10 simulaciones consecutivas con escenarios variados guiados por el modelo de Poisson.
        """
        print(f"[SimulationEngine] Iniciando proceso de 10 simulaciones cuantitativas para {local_team} vs {visitor_team}...")
        
        # 1. Obtener parámetros matemáticos estimables
        stats_params = self._extract_statistical_parameters(local_team, visitor_team, data_context)
        
        # Intentar cargar y calibrar el modelo Dixon-Coles
        import os
        import json
        historical_data_path = "historical_results.json"
        
        is_neutral = self._is_neutral_venue(local_team, visitor_team, data_context)
        if is_neutral:
            print(f"[SimulationEngine] Cancha neutral detectada. Se desactiva la ventaja de localía en Dixon-Coles.")
            
        if os.path.exists(historical_data_path):
            try:
                with open(historical_data_path, "r", encoding="utf-8") as f:
                    matches = json.load(f)
                
                from dixon_coles import DixonColesModel
                dc_model = DixonColesModel()
                dc_model.fit(matches, iterations=120)
                
                prediction = dc_model.predict_probabilities(local_team, visitor_team, neutral_venue=is_neutral)
                home_norm = dc_model.normalize_team(local_team)
                away_norm = dc_model.normalize_team(visitor_team)
                if home_norm in dc_model.attacks and away_norm in dc_model.attacks:
                    stats_params["local_expected_goals"] = prediction["home_lambda"]
                    stats_params["visitor_expected_goals"] = prediction["away_lambda"]
                    print(f"[SimulationEngine] Dixon-Coles base lambda (calibrado): {local_team}={stats_params['local_expected_goals']:.3f} | {visitor_team}={stats_params['visitor_expected_goals']:.3f}")
                else:
                    print(f"[SimulationEngine] Equipos no encontrados en la base de datos calibrada de Dixon-Coles. Usando estimación de goles de LLM ({stats_params['local_expected_goals']:.2f} vs {stats_params['visitor_expected_goals']:.2f}).")
            except Exception as e:
                print(f"[SimulationEngine] Advertencia: No se pudo calibrar Dixon-Coles ({e}). Usando lambdas de LLM.")
        else:
            print(f"[SimulationEngine] No se encontró historical_results.json. Usando lambdas de LLM.")
            
        # Ajuste dinámico por alineación titular oficial
        lineup_adj = self._calculate_lineup_adjustment(local_team, visitor_team, data_context.get("lineups", []))
        f_att_l = lineup_adj["f_attack_local"]
        f_def_l = lineup_adj["f_defense_local"]
        f_att_v = lineup_adj["f_attack_visitor"]
        f_def_v = lineup_adj["f_defense_visitor"]
        
        print(f"[SimulationEngine] Ajustes de alineación - Local (Att: {f_att_l:.2f}, Def: {f_def_l:.2f}) | Visitante (Att: {f_att_v:.2f}, Def: {f_def_v:.2f})")
        
        stats_params["local_expected_goals"] *= (f_att_l * f_def_v)
        stats_params["visitor_expected_goals"] *= (f_att_v * f_def_l)
        
        # Clip de prevención
        if stats_params["local_expected_goals"] < 0.1: stats_params["local_expected_goals"] = 0.1
        if stats_params["visitor_expected_goals"] < 0.1: stats_params["visitor_expected_goals"] = 0.1
            
        print(f"[SimulationEngine] Parámetros base finales (Alineación Ajustada): Lambda Local={stats_params['local_expected_goals']:.2f} | Lambda Visitante={stats_params['visitor_expected_goals']:.2f}")
        monte_carlo_stats = self._run_monte_carlo_simulation(
            stats_params["local_expected_goals"],
            stats_params["visitor_expected_goals"],
            stats_params["local_expected_corners"],
            stats_params["visitor_expected_corners"],
            stats_params["expected_cards"],
            stats_params.get("expected_fouls", 24.0)
        )
        print(f"[SimulationEngine] Monte Carlo (10k corridas) - Local Win: {monte_carlo_stats['probabilidad_victoria_local']:.1f}% | Empate: {monte_carlo_stats['probabilidad_empate']:.1f}% | Visitante Win: {monte_carlo_stats['probabilidad_victoria_visitante']:.1f}%")
        
        # Escenarios realistas con sus respectivos multiplicadores de rendimiento
        scenarios = [
            {"id": 1, "nombre": "Desarrollo estándar bajo clima neutral", "contexto": "Partido normal, sin incidentes iniciales extraordinarios.", "mult_local": 1.0, "mult_visitor": 1.0, "mult_corners": 1.0, "mult_cards": 1.0},
            {"id": 2, "nombre": "Clima extremo e impacto físico", "contexto": "El clima reportado afecta la cancha. Césped mojado/pesado, lo que incrementa faltas y tiros de esquina.", "mult_local": 0.8, "mult_visitor": 0.8, "mult_corners": 1.3, "mult_cards": 1.2},
            {"id": 3, "nombre": "Rigurosidad arbitral extrema", "contexto": "El árbitro designated aplica el reglamento de forma muy estricta. Alta probabilidad de tarjetas tempranas y penaltis.", "mult_local": 1.0, "mult_visitor": 1.0, "mult_corners": 0.9, "mult_cards": 2.0},
            {"id": 4, "nombre": "Lesión temprana de jugador clave", "contexto": "Un jugador clave del equipo local se lesiona en el minuto 15, obligando a un cambio táctico inesperado.", "mult_local": 0.7, "mult_visitor": 1.1, "mult_corners": 1.0, "mult_cards": 1.0},
            {"id": 5, "nombre": "Gol tempranero del visitante", "contexto": "El equipo visitante anota un gol antes del minuto 10, forzando al local a adelantar líneas tempranamente.", "mult_local": 1.2, "mult_visitor": 0.8, "mult_corners": 1.1, "mult_cards": 1.1},
            {"id": 6, "nombre": "Expulsión polémica en el primer tiempo", "contexto": "El árbitro expulsa a un defensor central del equipo local en el minuto 35 por doble amarilla polémica.", "mult_local": 0.6, "mult_visitor": 1.3, "mult_corners": 0.8, "mult_cards": 1.5},
            {"id": 7, "nombre": "Presión extrema de la afición local", "contexto": "Estadio lleno. El equipo local juega con una intensidad y presión alta asfixiante empujado por su afición.", "mult_local": 1.3, "mult_visitor": 0.8, "mult_corners": 1.2, "mult_cards": 1.1},
            {"id": 8, "nombre": "Rumor y distracción interna", "contexto": "Los rumores anímicos y noticias de vestuario afectan la concentración del equipo visitante en la defensa.", "mult_local": 1.2, "mult_visitor": 0.8, "mult_corners": 1.0, "mult_cards": 1.0},
            {"id": 9, "nombre": "Estrategia de contraataque letal", "contexto": "El equipo visitante cede la posesión por completo y busca transiciones rápidas. El local tiene la posesión pero es vulnerable.", "mult_local": 0.9, "mult_visitor": 1.2, "mult_corners": 1.1, "mult_cards": 1.0},
            {"id": 10, "nombre": "Partido de alta tensión y fricción táctica", "contexto": "Ambos equipos juegan a no perder. Marcado por faltas tácticas, muchos corners y pocos tiros a puerta claros.", "mult_local": 0.7, "mult_visitor": 0.7, "mult_corners": 1.3, "mult_cards": 1.4}
        ]

        valid_simulations = []

        for esc in scenarios:
            sim_id = esc["id"]
            sim_nombre = esc["nombre"]
            sim_contexto = esc["contexto"]
            
            # Calcular los lambdas ajustados por escenario
            esc_local_lambda = stats_params["local_expected_goals"] * esc["mult_local"]
            esc_visitor_lambda = stats_params["visitor_expected_goals"] * esc["mult_visitor"]
            esc_local_corners = stats_params["local_expected_corners"] * esc["mult_corners"]
            esc_visitor_corners = stats_params["visitor_expected_corners"] * esc["mult_corners"]
            esc_cards = stats_params["expected_cards"] * esc["mult_cards"]
            esc_fouls = stats_params.get("expected_fouls", 24.0) * esc.get("mult_cards", 1.0)
            
            # Inyectar guías estadísticas en el contexto para forzar que el LLM genere crónicas consistentes con los números
            esc_data_context = data_context.copy()
            esc_data_context["scenarios_guidelines"] = [
                f"REGLA DE PARADO DE MARCADOR: El partido debe terminar estrictamente con goles consistentes con Poisson para este escenario (Goles locales esperados: {esc_local_lambda:.2f}, Goles visitantes esperados: {esc_visitor_lambda:.2f}).",
                f"Corners locales esperados: {esc_local_corners:.1f}, Corners visitantes esperados: {esc_visitor_corners:.1f}",
                f"Tarjetas esperadas sumadas en el partido: {esc_cards:.1f}",
                f"Faltas esperadas sumadas en el partido: {esc_fouls:.1f}"
            ]
            if is_neutral:
                esc_data_context["scenarios_guidelines"].append("DETALLE DE TORNEO: El partido se juega en cancha neutral (Mundial / Selección). NO dar ventaja de localía clásica en las descripciones.")
            
            attempts = 0
            max_attempts = 4
            success = False
            current_simulation_data = None
            last_error_report = None

            while attempts < max_attempts and not success:
                attempts += 1
                try:
                    # 1. Generar simulación guiada
                    current_simulation_data = self._generate_simulation(
                        local_team, visitor_team, esc_data_context, tactical_analysis, 
                        sim_id, sim_nombre, sim_contexto, last_error_report, current_simulation_data
                    )
                    
                    # 2. Validar lógica
                    is_valid, error_report = self._validate_simulation_logic(
                        local_team, visitor_team, current_simulation_data
                    )
                    
                    if is_valid:
                        valid_simulations.append(current_simulation_data)
                        success = True
                    else:
                        print(f"[SimulationEngine] ADVERTENCIA: Fallo de consistencia en simulación {sim_id}: {error_report}")
                        last_error_report = error_report
                except Exception as e:
                    print(f"[SimulationEngine] ADVERTENCIA: Error en intento {attempts}: {e}")
                    last_error_report = f"Error de formato JSON: {str(e)}"
            
            if not success:
                # Fallback matemático puro si el LLM no logra estructurar
                print(f"[SimulationEngine] Alerta: Fallback matemático de último recurso (Poisson) para Simulación {sim_id}")
                import math
                import random
                def poisson_random(lmbda):
                    L = math.exp(-lmbda)
                    k = 0
                    p = 1.0
                    while p > L:
                        k += 1
                        p *= random.random()
                    return k - 1
                
                fallback_goals_local = max(0, poisson_random(esc_local_lambda))
                fallback_goals_visitor = max(0, poisson_random(esc_visitor_lambda))
                fallback_corners_local = max(0, poisson_random(esc_local_corners))
                fallback_corners_visitor = max(0, poisson_random(esc_visitor_corners))
                
                fallback_sim = {
                    "simulacion_id": sim_id,
                    "escenario": sim_nombre,
                    "goles_local": fallback_goals_local,
                    "goles_visitante": fallback_goals_visitor,
                    "anotadores": [],
                    "tarjetas_amarillas": [],
                    "tarjetas_rojas": [],
                    "tiros_esquina_local": fallback_corners_local,
                    "tiros_esquina_visitante": fallback_corners_visitor,
                    "posesion_local_porcentaje": 50,
                    "cronica_minuto_a_minuto": [f"Minuto 90: Simulación matemática directa (Poisson) debido a error técnico persistente del LLM."]
                }
                valid_simulations.append(fallback_sim)
                
        return SimulationList(valid_simulations, monte_carlo=monte_carlo_stats)

    def _generate_simulation(self, local: str, visitor: str, data: dict, tactics: dict, sim_id: int, nombre: str, contexto: str, error_report: str = None, previous_sim: dict = None) -> dict:
        """
        Llama al LLM para generar una simulación detallada del partido bajo ciertas variables.
        """
        referee_info = "\n".join(data.get("referee", []))
        weather_info = "\n".join(data.get("stadium_and_weather", []))
        rumors_info = "\n".join(data.get("player_rumors", []))
        lineups_info = "\n".join(data.get("lineups", []))
        guidelines_info = "\n".join(data.get("scenarios_guidelines", []))

        prompt = f"""
Simula el partido de fútbol entre:
Local: {local}
Visitante: {visitor}

Alineaciones titulares oficiales confirmadas de hoy:
{lineups_info}

Lineamientos Estadísticos del Escenario:
{guidelines_info}

Escenario de la Simulación {sim_id}: {nombre}
Condiciones especiales: {contexto}

Datos de internet del mundo real recopilados:
- Información del árbitro: {referee_info}
- Clima y estadio: {weather_info}
- Rumores e información anímica: {rumors_info}
- Parados tácticos previstos:
  * Formación {local}: {tactics.get('local_formacion')} (Estilo: {tactics.get('local_estilo')})
  * Formación {visitor}: {tactics.get('visitante_formacion')} (Estilo: {tactics.get('visitante_estilo')})

"""

        if error_report and previous_sim:
            prompt += f"""
ATENCIÓN: Tu simulación anterior fue RECHAZADA por tener fallas de lógica interna.
Simulación errónea anterior: {json.dumps(previous_sim, ensure_ascii=False)}
Reporte de errores lógicos a corregir: {error_report}

Por favor, corrige todos los fallos indicados y genera una nueva simulación coherente.
"""

        prompt += f"""
Debes simular el desarrollo minuto a minuto de las jugadas clave (goles, tarjetas, lesiones, corners) de manera realista e impredecible pero consistente con los Lineamientos Estadísticos del Escenario.

REGLAS DE PRECISIÓN Y REALISMO OBLIGATORIAS:
1. Usa ÚNICAMENTE nombres de jugadores reales que pertenezcan a la alineación titular o lista de convocados de los respectivos equipos provistas en los datos de internet. No inventes nombres ficticios.
2. Los eventos de la crónica minuto a minuto deben estar ordenados estrictamente en orden cronológico ascendente (de menor a mayor minuto).
3. Asegura que los minutos de todos los eventos estén dentro del rango lógico [1, 95].
4. Si un jugador recibe una tarjeta roja (expulsión), registra este evento con precisión en la lista `tarjetas_rojas` y en la crónica. A partir de ese minuto, ese jugador NO puede realizar ninguna otra acción (anotar goles, recibir tarjetas, participar activamente). Además, el equipo afectado debe reducir su volumen ofensivo y replegarse defensivamente.
5. No asignes más de una tarjeta amarilla al mismo jugador a menos que registres su expulsión automática por doble amonestación en el mismo minuto.
6. La sumatoria de goles en la lista de `anotadores` para cada equipo debe coincidir exactamente con los valores de `goles_local` y `goles_visitante`.

Devuelve el resultado estrictamente en el siguiente formato JSON (sin bloques markdown ni ```json adicionales, solo el texto JSON limpio):
{{
  "simulacion_id": {sim_id},
  "escenario": "{nombre}",
  "goles_local": 0,
  "goles_visitante": 0,
  "anotadores": [
    {{"minuto": 15, "jugador": "Nombre Jugador", "equipo": "local o visitante"}}
  ],
  "tarjetas_amarillas": [
    {{"minuto": 22, "jugador": "Nombre Jugador", "equipo": "local o visitante"}}
  ],
  "tarjetas_rojas": [
    {{"minuto": 35, "jugador": "Nombre Jugador", "equipo": "local o visitante", "motivo": "Falta táctica o doble amarilla"}}
  ],
  "tiros_esquina_local": 5,
  "tiros_esquina_visitante": 4,
  "posesion_local_porcentaje": 55,
  "cronica_minuto_a_minuto": [
    "Minuto 10: Descripción del juego...",
    "Minuto 15: Gol de...",
    "Minuto 90: Fin del partido..."
  ]
}}
"""

        system_instruction = "Eres un simulador de partidos de fútbol ultra preciso y realista. Debes responder exclusivamente con el JSON solicitado en español."
        raw_response = self.client.generate_content(prompt, system_instruction=system_instruction)

        clean_response = raw_response.strip()
        if clean_response.startswith("```"):
            lines = clean_response.splitlines()
            if lines[0].startswith("```json") or lines[0].startswith("```"):
                clean_response = "\n".join(lines[1:-1])

        try:
            return json.loads(clean_response)
        except Exception as e:
            print(f"[SimulationEngine] Error parseando respuesta del generador: {e}. Respuesta cruda: {clean_response}")
            raise e

    def _validate_simulation_logic(self, local: str, visitor: str, sim_data: dict) -> tuple:
        """
        Revisa que la simulación no contenga fallas de lógica futbolística.
        Retorna (es_valido: bool, reporte_error: str)
        """
        errors = []
        
        pos_local = sim_data.get("posesion_local_porcentaje", 50)
        if pos_local < 10 or pos_local > 90:
            errors.append("La posesión del equipo local está fuera de los rangos realistas (10% - 90%).")

        goles_local = sim_data.get("goles_local", 0)
        goles_visitante = sim_data.get("goles_visitante", 0)
        anotadores = sim_data.get("anotadores", [])
        
        goles_l_anotados = sum(1 for a in anotadores if a.get("equipo") == "local")
        goles_v_anotados = sum(1 for a in anotadores if a.get("equipo") == "visitante")
        
        if goles_l_anotados != goles_local:
            errors.append(f"Inconsistencia de goles locales: el marcador final indica {goles_local} pero la lista de anotadores locales tiene {goles_l_anotados}.")
        if goles_v_anotados != goles_visitante:
            errors.append(f"Inconsistencia de goles visitantes: el marcador final indica {goles_visitante} pero la lista de anotadores visitantes tiene {goles_v_anotados}.")

        # --- VALIDACIÓN DETERMINISTA DE FÚTBOL EN PYTHON ---
        red_card_minutes = {}  # jugador_name_clean: minuto
        player_yellows = {}    # jugador_name_clean: count
        
        # Tarjetas rojas
        for r in sim_data.get("tarjetas_rojas", []):
            m = r.get("minuto", 0)
            player = r.get("jugador", "").lower().strip()
            if m < 1 or m > 95:
                errors.append(f"Minuto de tarjeta roja inválido: {m} para el jugador {r.get('jugador')}.")
            if player:
                red_card_minutes[player] = m
                
        # Tarjetas amarillas
        for y in sim_data.get("tarjetas_amarillas", []):
            m = y.get("minuto", 0)
            player = y.get("jugador", "").lower().strip()
            if m < 1 or m > 95:
                errors.append(f"Minuto de tarjeta amarilla inválido: {m} para el jugador {y.get('jugador')}.")
            if player:
                player_yellows[player] = player_yellows.get(player, 0) + 1
                # Si tiene 2 amarillas y no hay roja
                if player_yellows[player] >= 2 and player not in red_card_minutes:
                    errors.append(f"El jugador {y.get('jugador')} acumuló {player_yellows[player]} tarjetas amarillas pero no registra tarjeta roja por expulsión.")
                # Tarjeta amarilla después de roja
                if player in red_card_minutes and m > red_card_minutes[player]:
                    errors.append(f"El jugador {y.get('jugador')} recibió tarjeta amarilla en el minuto {m}, después de haber sido expulsado en el minuto {red_card_minutes[player]}.")

        # Goles
        for a in sim_data.get("anotadores", []):
            m = a.get("minuto", 0)
            player = a.get("jugador", "").lower().strip()
            if m < 1 or m > 95:
                errors.append(f"Minuto de gol inválido: {m} para el gol de {a.get('jugador')}.")
            # Gol después de roja
            if player in red_card_minutes and m > red_card_minutes[player]:
                errors.append(f"El jugador {a.get('jugador')} anotó un gol en el minuto {m}, pero registra tarjeta roja (expulsado) en el minuto {red_card_minutes[player]}.")

        # Orden cronológico de la crónica minuto a minuto
        cronica = sim_data.get("cronica_minuto_a_minuto", [])
        last_min = 0
        import re
        for i, line in enumerate(cronica):
            # Buscar el primer número en la línea (suele ser "Minuto XX:" o "Min XX:")
            match = re.search(r'\b\d+\b', line)
            if match:
                curr_min = int(match.group(0))
                if curr_min < last_min:
                    errors.append(f"La crónica minuto a minuto tiene un error temporal: la línea {i+1} menciona el minuto {curr_min} después de haber narrado eventos del minuto {last_min}.")
                last_min = curr_min

        if errors:
            return False, "; ".join(errors)

        prompt = f"""
Analiza la siguiente simulación de un partido de fútbol y verifica si tiene inconsistencias lógicas o falta de realismo contextual con las condiciones físicas.
Inconsistencias a buscar:
1. Orden cronológico roto (ej. evento del minuto 70 antes del minuto 20 en la crónica).
2. Un jugador expulsado (tarjeta roja) que sigue jugando, recibe otra tarjeta después, o anota un gol después de su minuto de expulsión.
3. El marcador final no coincide con el desarrollo de la crónica minuto a minuto.
4. Datos estadísticos absurdos (ej. 50 tiros de esquina o posesión del 100%).
5. Inconsistencia física contextual: Si el escenario involucra clima extremo (lluvia/viento fuerte) y el total de corners es menor a 5, o si el escenario involucra rigurosidad arbitral extrema y hay menos de 3 tarjetas en total, debes rechazarlo por falta de realismo táctico y disciplinario.

Datos de la simulación:
{json.dumps(sim_data, ensure_ascii=False)}

Devuelve únicamente un JSON con este formato (sin bloques markdown ni ```json adicionales):
{{
  "es_valido": true o false,
  "motivo_rechazo": "Descripción del fallo de lógica o consistencia si es_valido es false, de lo contrario dejar en blanco"
}}
"""

        system_instruction = "Eres un inspector de consistencia deportiva estricto. Responde únicamente en JSON y en español."
        raw_response = self.client.generate_content(prompt, system_instruction=system_instruction)

        clean_response = raw_response.strip()
        if clean_response.startswith("```"):
            lines = clean_response.splitlines()
            if lines[0].startswith("```json") or lines[0].startswith("```"):
                clean_response = "\n".join(lines[1:-1])

        try:
            val_res = json.loads(clean_response)
            return val_res.get("es_valido", True), val_res.get("motivo_rechazo", "")
        except Exception as e:
            print(f"[SimulationEngine] Error parseando respuesta del validador: {e}")
            return True, ""

    def _is_neutral_venue(self, local: str, visitor: str, raw_data: dict) -> bool:
        """
        Detecta si el partido se juega en cancha neutral (Mundial, Copa América, Euro, etc.).
        """
        if raw_data and raw_data.get("neutral_venue_override", False):
            return True
        text_corpus = f"{local} {visitor}".lower()
        for key, snippets in raw_data.items():
            if isinstance(snippets, list):
                for item in snippets:
                    if isinstance(item, str):
                        text_corpus += " " + item.lower()
                    elif isinstance(item, dict) and "content" in item:
                        text_corpus += " " + str(item["content"]).lower()
                
        # Palabras clave de torneos neutrales o indicaciones de mundial
        neutral_keywords = [
            "mundial", "world cup", "copa del mundo", "copa mundial", 
            "neutral venue", "cancha neutral", "estadio neutral", 
            "copa america", "copa américa", "eurocopa", "juegos olímpicos"
        ]
        for kw in neutral_keywords:
            if kw in text_corpus:
                return True
                
        # Si ambos equipos son selecciones nacionales
        countries = {
            "argentina", "francia", "alemania", "mexico", "méxico", "brasil", "españa", "espana", "portugal",
            "italia", "inglaterra", "países bajos", "paises bajos", "holanda", "belgica", "bélgica", "croacia",
            "marruecos", "senegal", "colombia", "uruguay", "chile", "ecuador", "peru", "perú", "venezuela",
            "paraguay", "bolivia", "estados unidos", "usa", "canada", "canadá", "japon", "japón", "corea del sur",
            "australia", "arabia saudita", "egipto", "camerún", "camerun", "ghana", "costa de marfil", "argelia",
            "nigeria", "túnez", "tunez", "suecia", "suiza", "polonia", "dinamarca", "noruega", "ucrania", "turquía",
            "turquia", "gales", "escocia", "irlanda", "república checa", "republica checa", "austria", "grecia",
            "rumanía", "rumania", "bulgaria", "hungría", "hungria", "eslovaquia", "eslovenia", "finlandia",
            "islandia", "serbia", "albania", "georgia", "qatar", "irán", "iran", "irak", "iraq",
            "arabia saudí", "china", "india", "sudáfrica", "sudafrica", "nueva zelanda", "honduras", "costa rica",
            "panamá", "panama", "jamaica", "el salvador", "guatemala", "marruecos"
        }
        
        local_clean = "".join(c for c in local.lower() if c.isalnum() or c.isspace()).strip()
        visitor_clean = "".join(c for c in visitor.lower() if c.isalnum() or c.isspace()).strip()
        
        is_local_country = local_clean in countries or any(c in local_clean for c in countries)
        is_visitor_country = visitor_clean in countries or any(c in visitor_clean for c in countries)
        
        if is_local_country and is_visitor_country:
            return True
            
        # Si se juega en estadios de México pero ninguno de los dos equipos es de México
        stadium_text = " ".join(raw_data.get("stadium_and_weather", [])).lower()
        if "mexico" in stadium_text or "méxico" in stadium_text:
            if "mexico" not in local.lower() and "méxico" not in local.lower() and "mexico" not in visitor.lower() and "méxico" not in visitor.lower():
                return True
                
        return False
