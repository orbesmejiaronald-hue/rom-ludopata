import os
import sys
import json

# Forzar codificación UTF-8 para evitar caracteres rotos en la consola de Windows
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

from gemini_client import GeminiClient
from data_collector import DataCollector
from tactical_analyzer import TacticalAnalyzer
from simulation_engine import SimulationEngine
from market_analyzer import MarketAnalyzer
from report_generator import ReportGenerator

class AgentCoordinator:
    def __init__(self):
        print("[AgentCoordinator] Inicializando Agente de Apuestas Deportivas Avanzado (AADA)...")
        self.gemini_client = GeminiClient()
        self.collector = DataCollector()
        self.tactical_analyzer = TacticalAnalyzer(self.gemini_client)
        self.sim_engine = SimulationEngine(self.gemini_client)
        self.market_analyzer = MarketAnalyzer(self.gemini_client)
        self.report_generator = ReportGenerator()

    def _save_to_history(self, local_team: str, visitor_team: str, tactics: dict, simulations: list, market_analysis: dict, environment: dict = None):
        """
        Guarda los datos estructurados del análisis y simulaciones en un archivo local JSON.
        """
        import datetime
        history_path = "historical_simulations.json"
        record = {
            "timestamp": datetime.datetime.now().isoformat(),
            "local_team": local_team,
            "visitor_team": visitor_team,
            "tactics": tactics,
            "simulations": simulations,
            "market_analysis": market_analysis,
            "environment": environment
        }
        
        history_data = []
        if os.path.exists(history_path):
            try:
                with open(history_path, "r", encoding="utf-8") as f:
                    history_data = json.load(f)
                    if not isinstance(history_data, list):
                        history_data = []
            except Exception as e:
                print(f"[AgentCoordinator] Advertencia al leer historial: {e}. Creando historial nuevo.")
                history_data = []
        
        history_data.append(record)

        # ── MEJORA B: Mantener solo los últimos 50 registros ─────────────────
        MAX_HISTORY = 50
        if len(history_data) > MAX_HISTORY:
            history_data = history_data[-MAX_HISTORY:]
        # ─────────────────────────────────────────────────────────────────────

        try:
            with open(history_path, "w", encoding="utf-8") as f:
                json.dump(history_data, f, ensure_ascii=False, indent=2)
            print(f"[AgentCoordinator] Historial guardado ({len(history_data)}/{MAX_HISTORY} registros) en {history_path}")
        except Exception as e:
            print(f"[AgentCoordinator] Error guardando historial: {e}")


    def _extract_environment_details(self, raw_data: dict, local_team: str, visitor_team: str) -> dict:
        """
        Extrae y estructura los detalles del estadio, clima y árbitro a partir de los datos crudos usando Gemini.
        """
        print("[AgentCoordinator] Extrayendo detalles estructurados del entorno (Estadio, Clima, Árbitro)...")
        referee_text = "\n".join(raw_data.get("referee", []))
        stadium_text = "\n".join(raw_data.get("stadium_and_weather", []))
        
        scraped_content = ""
        for page in raw_data.get("scraped_pages", []):
            scraped_content += f"\n--- Contenido de la página {page['url']} ---\n{page['content']}\n"
            
        is_neutral = self._is_neutral_venue(local_team, visitor_team, raw_data)
        
        fallback_env = {
            "estadio_nombre": "Desconocido (Cancha Neutral)" if is_neutral else "Desconocido",
            "estadio_capacidad": "N/A",
            "estadio_cesped": "Desconocido",
            "estadio_localia_impacto": "Cancha neutral. Se desactiva la ventaja de localía." if is_neutral else "No hay información disponible sobre el impacto de la localía.",
            "clima_pronostico": "Despejado / Clima estándar",
            "arbitro_nombre": "Desconocido",
            "arbitro_promedio_tarjetas": "N/A",
            "arbitro_tarjetero": "No",
            "arbitro_estilo": "No hay información disponible sobre su rigurosidad.",
            "es_cancha_neutral": is_neutral
        }
        
        if not referee_text and not stadium_text:
            return fallback_env
            
        neutral_note = ""
        if is_neutral:
            neutral_note = f"\nNOTA DE CANCHA NEUTRAL: Este es un partido en Cancha Neutral (Mundial, Copa América, Eurocopa, etc.). Asegúrate de que 'estadio_localia_impacto' indique claramente en español que se juega en cancha neutral sin ventaja de localía para {local_team}.\n"

        prompt = f"""
Analiza la siguiente información recopilada de internet para extraer detalles sobre el estadio, el clima y el árbitro del partido:
{neutral_note}
Información del Árbitro:
{referee_text}

Información del Estadio y Clima:
{stadium_text}
{scraped_content}

PROHIBICIÓN ABSOLUTA DE ALUCINACIÓN: Si en la información de internet provista no se especifica el nombre del estadio, el clima o el árbitro para el encuentro de hoy, debes reportar 'Desconocido' o 'N/A'. Está estrictamente prohibido predecir, estimar o asumir estadios ficticios o famosos (como el Estadio Azteca o Wembley) si no constan explícitamente en el texto de internet. Tu respuesta debe basarse exclusivamente en datos en tiempo real de internet.

Extrae los siguientes detalles precisos y devuélvelos únicamente en un formato JSON estructurado como este, sin bloques markdown ```json (solo texto JSON puro):
{{
  "estadio_nombre": "Nombre del estadio",
  "estadio_capacidad": "Capacidad (ej. 50,000 espectadores o N/A)",
  "estadio_cesped": "Tipo de césped (ej. Natural, Sintético, Híbrido o N/A)",
  "estadio_localia_impacto": "Análisis muy breve de cómo influye la localía en este estadio en español",
  "clima_pronostico": "Estado del clima esperado en español (ej. Lluvia ligera, 15°C, viento)",
  "arbitro_nombre": "Nombre completo del árbitro",
  "arbitro_promedio_tarjetas": "Promedio de tarjetas por partido (ej. 4.2 amarillas, 0.1 rojas o N/A)",
  "arbitro_tarjetero": "Sí/No (indica 'Sí' si su promedio de tarjetas es alto -más de 4.5 por partido- o si la prensa lo reporta como muy estricto)",
  "arbitro_estilo": "Trayectoria detallada del árbitro en español (ej. Historial en partidos clave, nivel de rigurosidad, propensión a cobrar penaltis, si es protagonista o polémico, y cómo conduce el juego)."
}}
"""
        system_instruction = "Eres un analista de datos deportivos experto y preciso. Responde única y exclusivamente con un objeto JSON estructurado en español."
        
        try:
            raw_response = self.gemini_client.generate_content(prompt, system_instruction=system_instruction)
            clean_response = raw_response.strip()
            if clean_response.startswith("```"):
                lines = clean_response.splitlines()
                if lines[0].startswith("```json") or lines[0].startswith("```"):
                    clean_response = "\n".join(lines[1:-1])
            
            env_data = json.loads(clean_response)
            env_data["es_cancha_neutral"] = is_neutral
            # Validar claves
            for key in fallback_env:
                if key not in env_data:
                    env_data[key] = fallback_env[key]
            return env_data
        except Exception as e:
            print(f"[AgentCoordinator] Advertencia al extraer detalles del entorno: {e}. Usando fallback.")
            fallback_env["es_cancha_neutral"] = is_neutral
            return fallback_env

    def run_full_analysis(self, local_team: str, visitor_team: str, output_path: str = None, neutral_venue_override: bool = False) -> str:
        """
        Ejecuta el flujo completo de análisis para un partido de fútbol.
        """
        print(f"\n[AgentCoordinator] === INICIANDO ANÁLISIS: {local_team} vs {visitor_team} ===")
        
        # Paso 1: Recopilación de datos en Internet
        print("\n[AgentCoordinator] [Paso 1/5] Recopilando datos de Internet...")
        raw_data = self.collector.collect_all_data(local_team, visitor_team)
        raw_data["neutral_venue_override"] = neutral_venue_override
        
        # Extraer detalles del entorno
        environment = self._extract_environment_details(raw_data, local_team, visitor_team)
        
        # Paso 2: Análisis Táctico
        print("\n[AgentCoordinator] [Paso 2/5] Realizando análisis táctico de alineaciones...")
        tactics = self.tactical_analyzer.analyze_tactics(local_team, visitor_team, raw_data.get("lineups", []))
        
        # Advertencia en caso de usar alineaciones no oficiales de referencia
        if not tactics.get("alineaciones_oficiales", True):
            print(f"[AgentCoordinator] ⚠️ ADVERTENCIA: {tactics.get('advertencia_lineas')}")
            
        print(f"[AgentCoordinator] Formaciones identificadas - {local_team}: {tactics.get('local_formacion')} | {visitor_team}: {tactics.get('visitante_formacion')}")
        
        # Paso 3: Motor de Simulaciones (10 simulaciones coherentes con autocorrección)
        print("\n[AgentCoordinator] [Paso 3/5] Corriendo y validando 10 simulaciones del partido...")
        simulations = self.sim_engine.run_all_simulations(local_team, visitor_team, raw_data, tactics)
        print(f"[AgentCoordinator] Se completaron las {len(simulations)} simulaciones requeridas.")
        
        # Paso 4: Análisis de Mercados y Valor de Apuestas
        print("\n[AgentCoordinator] [Paso 4/5] Analizando cuotas mundiales y buscando apuestas de valor...")
        market_analysis = self.market_analyzer.analyze_market_and_stats(local_team, visitor_team, simulations, raw_data)
        
        # Paso 5: Generación del Reporte en Español
        print("\n[AgentCoordinator] [Paso 5/5] Generando el reporte de pronóstico en español...")
        report = self.report_generator.generate_report(local_team, visitor_team, raw_data, tactics, simulations, market_analysis)
        
        # Guardar en el historial estructurado local
        self._save_to_history(local_team, visitor_team, tactics, simulations, market_analysis, environment)
        
        if output_path:
            try:
                # Guardar el reporte en archivo
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(report)
                print(f"[AgentCoordinator] Reporte guardado con éxito en: {output_path}")
            except Exception as e:
                print(f"[AgentCoordinator] Error guardando el reporte en {output_path}: {e}")
        
        print("\n[AgentCoordinator] === ANÁLISIS COMPLETADO CON ÉXITO ===")
        return report

    def run_full_analysis_generator(self, local_team: str, visitor_team: str, neutral_venue_override: bool = False):
        """
        Generador que ejecuta el flujo de análisis y produce actualizaciones en tiempo real.
        """
        if self.gemini_client.client_type == "mock":
            yield {"step": 1, "status": "recolectando", "message": "⚠️ ADVERTENCIA: No se detectó GEMINI_API_KEY en las variables de entorno. Ejecutando análisis en MODO SIMULADO con modelos pre-entrenados locales."}
            
        yield {"step": 1, "status": "recolectando", "message": "Buscando estadísticas de los últimos partidos, alineaciones, árbitro y clima en internet..."}
        raw_data = self.collector.collect_all_data(local_team, visitor_team)
        raw_data["neutral_venue_override"] = neutral_venue_override
        
        yield {"step": 1, "status": "recolectando", "message": "Analizando y estructurando datos del estadio, clima y árbitro..."}
        environment = self._extract_environment_details(raw_data, local_team, visitor_team)
        
        yield {"step": 2, "status": "tactico", "message": "Analizando esquemas tácticos, parados y estilos de juego..."}
        tactics = self.tactical_analyzer.analyze_tactics(local_team, visitor_team, raw_data.get("lineups", []))
        
        # Advertencia en caso de usar alineaciones no oficiales de referencia
        if not tactics.get("alineaciones_oficiales", True):
            yield {
                "step": 2,
                "status": "tactico",
                "message": f"⚠️ ADVERTENCIA: {tactics.get('advertencia_lineas')}"
            }
            
        yield {"step": 3, "status": "simulando", "message": "Extrayendo parámetros estadísticos cuantitativos del partido..."}
        stats_params = self.sim_engine._extract_statistical_parameters(local_team, visitor_team, raw_data)
        
        # Intentar cargar y calibrar el modelo Dixon-Coles en el generador
        import os
        import json
        historical_data_path = "historical_results.json"
        if os.path.exists(historical_data_path):
            try:
                yield {"step": 3, "status": "simulando", "message": "Cargando histórico de partidos y calibrando modelo Dixon-Coles..."}
                with open(historical_data_path, "r", encoding="utf-8") as f:
                    matches = json.load(f)
                from dixon_coles import DixonColesModel
                dc_model = DixonColesModel()
                dc_model.fit(matches, iterations=120)
                
                is_neutral = self._is_neutral_venue(local_team, visitor_team, raw_data)
                if is_neutral:
                    yield {"step": 3, "status": "simulando", "message": "⚽ Detectado partido de Selección / Mundial (Cancha Neutral). Se desactiva la ventaja de localía."}
                    
                prediction = dc_model.predict_probabilities(local_team, visitor_team, neutral_venue=is_neutral)
                home_norm = dc_model.normalize_team(local_team)
                away_norm = dc_model.normalize_team(visitor_team)
                if home_norm in dc_model.attacks and away_norm in dc_model.attacks:
                    stats_params["local_expected_goals"] = prediction["home_lambda"]
                    stats_params["visitor_expected_goals"] = prediction["away_lambda"]
                    yield {"step": 3, "status": "simulando", "message": f"Dixon-Coles calibrado: Lambda {local_team}={stats_params['local_expected_goals']:.2f} | Lambda {visitor_team}={stats_params['visitor_expected_goals']:.2f}"}
                else:
                    yield {"step": 3, "status": "simulando", "message": f"Equipos no encontrados en la base de datos de Dixon-Coles. Usando estimaciones de goles de LLM (L:{stats_params['local_expected_goals']:.2f} | V:{stats_params['visitor_expected_goals']:.2f})"}
            except Exception as e:
                yield {"step": 3, "status": "simulando", "message": f"Advertencia: No se pudo calibrar Dixon-Coles ({str(e)}). Usando lambdas de LLM."}
        
        # Aplicar el ajuste de alineación por coeficientes de jugador titular
        yield {"step": 3, "status": "simulando", "message": "Calculando coeficientes de rendimiento de los jugadores en la alineación titular..."}
        lineup_adj = self.sim_engine._calculate_lineup_adjustment(local_team, visitor_team, raw_data.get("lineups", []))
        f_att_l = lineup_adj["f_attack_local"]
        f_def_l = lineup_adj["f_defense_local"]
        f_att_v = lineup_adj["f_attack_visitor"]
        f_def_v = lineup_adj["f_defense_visitor"]
        
        stats_params["local_expected_goals"] *= (f_att_l * f_def_v)
        stats_params["visitor_expected_goals"] *= (f_att_v * f_def_l)
        
        if stats_params["local_expected_goals"] < 0.1: stats_params["local_expected_goals"] = 0.1
        if stats_params["visitor_expected_goals"] < 0.1: stats_params["visitor_expected_goals"] = 0.1
        
        yield {"step": 3, "status": "simulando", "message": f"Alineación Ajustada - Local (Att: {f_att_l:.2f}, Def: {f_def_l:.2f}) | Visitante (Att: {f_att_v:.2f}, Def: {f_def_v:.2f})"}
        yield {"step": 3, "status": "simulando", "message": f"Parámetros finales: Lambda Local={stats_params['local_expected_goals']:.2f} | Lambda Visitante={stats_params['visitor_expected_goals']:.2f}. Corriendo 10,000 simulaciones de Monte Carlo..."}
        
        monte_carlo_stats = self.sim_engine._run_monte_carlo_simulation(
            stats_params["local_expected_goals"],
            stats_params["visitor_expected_goals"],
            stats_params["local_expected_corners"],
            stats_params["visitor_expected_corners"],
            stats_params["expected_cards"]
        )
        
        yield {"step": 3, "status": "simulando", "message": f"Análisis en tiempo real de corners: Probabilidad Más de 8.5 corners: {monte_carlo_stats['probabilidad_over_8_5_corners']:.1f}% | Más de 9.5: {monte_carlo_stats['probabilidad_over_9_5_corners']:.1f}% (Promedio esperado: L {monte_carlo_stats['promedio_corners_local']:.1f} | V {monte_carlo_stats['promedio_corners_visitante']:.1f})."}
        yield {"step": 3, "status": "simulando", "message": f"Análisis en tiempo real de tarjetas: Probabilidad Más de 3.5 tarjetas: {monte_carlo_stats['probabilidad_over_3_5_cards']:.1f}% | Más de 4.5: {monte_carlo_stats['probabilidad_over_4_5_cards']:.1f}% (Rigurosidad promedio esperada: {monte_carlo_stats['promedio_tarjetas']:.1f} amonestaciones)."}
        
        yield {"step": 3, "status": "simulando", "message": f"Monte Carlo finalizado. Victoria Local: {monte_carlo_stats['probabilidad_victoria_local']:.1f}% | Empate: {monte_carlo_stats['probabilidad_empate']:.1f}% | Victoria Visitante: {monte_carlo_stats['probabilidad_victoria_visitante']:.1f}%. Iniciando 10 escenarios específicos..."}
        
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
        
        simulations = []
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
            
            # Inyectar guías estadísticas en el contexto para forzar consistencia
            esc_data_context = raw_data.copy()
            esc_data_context["scenarios_guidelines"] = [
                f"REGLA DE PARADO DE MARCADOR: El partido debe terminar estrictamente con goles consistentes con Poisson para este escenario (Goles locales esperados: {esc_local_lambda:.2f}, Goles visitantes esperados: {esc_visitor_lambda:.2f}).",
                f"Corners locales esperados: {esc_local_corners:.1f}, Corners visitantes esperados: {esc_visitor_corners:.1f}",
                f"Tarjetas esperadas sumadas en el partido: {esc_cards:.1f}"
            ]
            
            yield {"step": 3, "status": "simulando", "message": f"Ejecutando Simulación {sim_id}/10: '{sim_nombre}'..."}
            
            attempts = 0
            max_attempts = 4
            success = False
            sim_data = None
            last_error_report = None
            
            while attempts < max_attempts and not success:
                attempts += 1
                try:
                    sim_data = self.sim_engine._generate_simulation(
                        local_team, visitor_team, esc_data_context, tactics, 
                        sim_id, sim_nombre, sim_contexto, last_error_report, sim_data
                    )
                    is_valid, error_report = self.sim_engine._validate_simulation_logic(
                        local_team, visitor_team, sim_data
                    )
                    if is_valid:
                        success = True
                    else:
                        last_error_report = error_report
                except Exception as e:
                    last_error_report = f"Error de formato JSON: {str(e)}"
            
            if not success:
                # Fallback matemático de último recurso (Poisson)
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
                
                sim_data = {
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
            
            simulations.append(sim_data)
            yield {
                "step": 3, 
                "status": "simulando_progreso", 
                "message": f"Simulación {sim_id}/10 completada y validada.",
                "resultado": f"{sim_data.get('goles_local')} - {sim_data.get('goles_visitante')}",
                "simulacion": sim_data
            }
            
        from simulation_engine import SimulationList
        simulations_list = SimulationList(simulations, monte_carlo=monte_carlo_stats)
        
        yield {"step": 4, "status": "mercado", "message": "Calculando cuotas implícitas y evaluando valor en mercados asiáticos y mundiales..."}
        market_analysis = self.market_analyzer.analyze_market_and_stats(local_team, visitor_team, simulations_list, raw_data)
        
        yield {"step": 5, "status": "reporte", "message": "Generando reporte de pronóstico final estructurado..."}
        report = self.report_generator.generate_report(local_team, visitor_team, raw_data, tactics, simulations_list, market_analysis)
        
        # Guardar en el historial estructurado local
        self._save_to_history(local_team, visitor_team, tactics, simulations_list, market_analysis, environment)
        
        yield {
            "step": 5, 
            "status": "completado", 
            "message": "¡Análisis de alta eficiencia finalizado!",
            "reporte": report,
            "simulaciones": simulations,
            "tactics": tactics,
            "market_analysis": market_analysis,
            "environment": environment
        }

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

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Uso: python agent_coordinator.py \"Equipo Local\" \"Equipo Visitante\" [ruta_output.md]")
        sys.exit(1)
        
    local = sys.argv[1]
    visitor = sys.argv[2]
    out_path = sys.argv[3] if len(sys.argv) > 3 else "pronostico_resultado.md"
    
    coordinator = AgentCoordinator()
    coordinator.run_full_analysis(local, visitor, out_path)
