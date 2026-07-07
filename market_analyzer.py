import json
from gemini_client import GeminiClient

class MarketAnalyzer:
    def __init__(self, gemini_client: GeminiClient):
        self.client = gemini_client

    def analyze_market_and_stats(self, local_team: str, visitor_team: str, simulations: list, data_context: dict) -> dict:
        """
        Calcula estadísticas de las simulaciones y las compara con cuotas del mercado real/asiático para identificar valor.
        """
        print(f"[MarketAnalyzer] Analizando estadísticas agregadas y mercado de apuestas para {local_team} vs {visitor_team}...")
        
        num_sims = len(simulations)
        if num_sims == 0:
            return {}

        # 1. Calcular métricas agregadas básicas de las simulaciones
        monte_carlo = getattr(simulations, "monte_carlo", None)
        
        if monte_carlo:
            prob_local = monte_carlo["probabilidad_victoria_local"]
            prob_visitor = monte_carlo["probabilidad_victoria_visitante"]
            prob_draw = monte_carlo["probabilidad_empate"]
            prob_over_1_5 = monte_carlo["probabilidad_over_1_5"]
            prob_over_2_5 = monte_carlo["probabilidad_over_2_5"]
            
            prob_over_8_5_corners = monte_carlo.get("probabilidad_over_8_5_corners", 50.0)
            prob_over_9_5_corners = monte_carlo.get("probabilidad_over_9_5_corners", 40.0)
            prob_over_10_5_corners = monte_carlo.get("probabilidad_over_10_5_corners", 30.0)
            
            prob_over_3_5_cards = monte_carlo.get("probabilidad_over_3_5_cards", 60.0)
            prob_over_4_5_cards = monte_carlo.get("probabilidad_over_4_5_cards", 50.0)
            prob_over_5_5_cards = monte_carlo.get("probabilidad_over_5_5_cards", 40.0)
            
            avg_goals_local = monte_carlo.get("promedio_goles_local", 1.5)
            avg_goals_visitor = monte_carlo.get("promedio_goles_visitante", 1.1)
            avg_corners_local = monte_carlo["promedio_corners_local"]
            avg_corners_visitor = monte_carlo["promedio_corners_visitante"]
            avg_yellow_cards = monte_carlo["promedio_tarjetas"]
            avg_red_cards = 0.1  # estimación promedio razonable para rojas
        else:
            home_wins = 0
            away_wins = 0
            draws = 0
            total_goals = 0
            total_goals_local = 0
            total_goals_visitor = 0
            over_1_5 = 0
            over_2_5 = 0
            total_corners_local = 0
            total_corners_visitor = 0
            total_yellow_cards = 0
            total_red_cards = 0
            
            over_8_5_corn = 0
            over_9_5_corn = 0
            over_10_5_corn = 0
            over_3_5_card = 0
            over_4_5_card = 0
            over_5_5_card = 0
            
            for sim in simulations:
                g_local = sim.get("goles_local", 0)
                g_visitor = sim.get("goles_visitante", 0)
                
                # Resultado 1X2
                if g_local > g_visitor:
                    home_wins += 1
                elif g_visitor > g_local:
                    away_wins += 1
                else:
                    draws += 1

                total_goals += (g_local + g_visitor)
                total_goals_local += g_local
                total_goals_visitor += g_visitor
                if (g_local + g_visitor) > 1.5:
                    over_1_5 += 1
                if (g_local + g_visitor) > 2.5:
                    over_2_5 += 1

                # Corners
                c_l = sim.get("tiros_esquina_local", 5)
                c_v = sim.get("tiros_esquina_visitante", 4)
                total_corners_local += c_l
                total_corners_visitor += c_v
                
                total_c = c_l + c_v
                if total_c > 8.5: over_8_5_corn += 1
                if total_c > 9.5: over_9_5_corn += 1
                if total_c > 10.5: over_10_5_corn += 1

                # Tarjetas
                y_c = len(sim.get("tarjetas_amarillas", []))
                r_c = len(sim.get("tarjetas_rojas", []))
                total_yellow_cards += y_c
                total_red_cards += r_c
                
                cards_total = y_c + r_c
                if cards_total > 3.5: over_3_5_card += 1
                if cards_total > 4.5: over_4_5_card += 1
                if cards_total > 5.5: over_5_5_card += 1

            # Porcentajes de probabilidad propios
            prob_local = (home_wins / num_sims) * 100
            prob_visitor = (away_wins / num_sims) * 100
            prob_draw = (draws / num_sims) * 100
            prob_over_1_5 = (over_1_5 / num_sims) * 100
            prob_over_2_5 = (over_2_5 / num_sims) * 100

            prob_over_8_5_corners = (over_8_5_corn / num_sims) * 100
            prob_over_9_5_corners = (over_9_5_corn / num_sims) * 100
            prob_over_10_5_corners = (over_10_5_corn / num_sims) * 100
            prob_over_3_5_cards = (over_3_5_card / num_sims) * 100
            prob_over_4_5_cards = (over_4_5_card / num_sims) * 100
            prob_over_5_5_cards = (over_5_5_card / num_sims) * 100

            avg_goals_local = total_goals_local / num_sims
            avg_goals_visitor = total_goals_visitor / num_sims
            avg_corners_local = total_corners_local / num_sims
            avg_corners_visitor = total_corners_visitor / num_sims
            avg_yellow_cards = total_yellow_cards / num_sims
            avg_red_cards = total_red_cards / num_sims

        # 2. Consultar cuotas reales del mercado mundial y hándicap asiático usando Gemini
        referee_text = "\n".join(data_context.get("referee", []))
        weather_text = "\n".join(data_context.get("stadium_and_weather", []))
        
        prompt = f"""
Actúa como un apostador profesional veterano (sharp bettor) con décadas de experiencia en mercados mundiales y hándicap asiático. Tu enfoque es puramente matemático, pragmático y frío. No te dejas llevar por sentimentalismos de los fanáticos ni el favoritismo del público general (dinero del público que infla cuotas de equipos famosos por reputación).

Analiza y estima el valor real de las cuotas para el partido:
Local: {local_team}
Visitante: {visitor_team}

Estadísticas crudas de nuestras simulaciones internas:
- Probabilidad de victoria Local: {prob_local}%
- Probabilidad de victoria Visitante: {prob_visitor}%
- Probabilidad de Empate: {prob_draw}%
- Probabilidad de Más de 2.5 goles: {prob_over_2_5}%
- Probabilidad de Más de 8.5 corners: {prob_over_8_5_corners}%
- Probabilidad de Más de 9.5 corners: {prob_over_9_5_corners}%
- Probabilidad de Más de 10.5 corners: {prob_over_10_5_corners}%
- Probabilidad de Más de 3.5 tarjetas: {prob_over_3_5_cards}%
- Probabilidad de Más de 4.5 tarjetas: {prob_over_4_5_cards}%
- Probabilidad de Más de 5.5 tarjetas: {prob_over_5_5_cards}%

Por favor, busca en internet o estima basado en el rendimiento histórico y la situación actual, las cuotas de las casas de apuestas (mercado real) para:
1. Cuotas 1X2 (Local, Empate, Visitante).
2. Cuotas de Hándicap Asiático principales.
3. Cuotas de Más/Menos (Over/Under) 2.5 Goles.
4. Cuotas de Más/Menos 9.5 Corners y 4.5 Tarjetas.

Compara la "Probabilidad Implícita" de la cuota de la casa de apuestas (Probabilidad Implícita = 100 / Cuota) contra nuestras probabilidades simuladas.
Encuentra "Apuestas de Valor" (Value Bets) en mercados principales y secundarios (corners o tarjetas).
Advierte si hay una "Trampa de Cuota".

Devuelve tu respuesta únicamente en un formato JSON estructurado como este (sin bloques markdown ```json adicionales):
{{
  "cuota_local_estimada": 1.95,
  "cuota_empate_estimada": 3.40,
  "cuota_visitante_estimada": 3.80,
  "handicap_asiatico_linea": "{local_team} -0.5",
  "handicap_asiatico_cuota": 1.90,
  "cuota_over_2_5_estimada": 2.05,
  "cuota_under_2_5_estimada": 1.75,
  "cuota_over_9_5_corners_estimada": 1.85,
  "cuota_under_9_5_corners_estimada": 1.95,
  "cuota_over_4_5_tarjetas_estimada": 1.90,
  "cuota_under_4_5_tarjetas_estimada": 1.90,
  "comparativa_valor": [
    "Análisis frío: ..."
  ],
  "recomendacion_apuesta": "Recomendación final pragmática redactada en español basada estrictamente en valor matemático."
}}
"""

        system_instruction = "Eres un apostador veterano profesional, astuto y analítico (sharp bettor). Responde exclusivamente en español y en formato JSON válido."
        raw_response = self.client.generate_content(prompt, system_instruction=system_instruction)

        clean_response = raw_response.strip()
        if clean_response.startswith("```"):
            lines = clean_response.splitlines()
            if lines[0].startswith("```json") or lines[0].startswith("```"):
                clean_response = "\n".join(lines[1:-1])

        try:
            market_data = json.loads(clean_response)
            if not isinstance(market_data, dict) or "cuota_local_estimada" not in market_data:
                raise ValueError("JSON de mercado incompleto o vacío")
            
            # Asegurar la existencia de cuotas secundarias en el market_data parsed
            if "cuota_over_9_5_corners_estimada" not in market_data:
                market_data["cuota_over_9_5_corners_estimada"] = round(100.0 / prob_over_9_5_corners, 2) if prob_over_9_5_corners > 5 else 1.90
            if "cuota_under_9_5_corners_estimada" not in market_data:
                market_data["cuota_under_9_5_corners_estimada"] = round(100.0 / (100.0 - prob_over_9_5_corners), 2) if prob_over_9_5_corners < 95 else 1.90
            if "cuota_over_4_5_tarjetas_estimada" not in market_data:
                market_data["cuota_over_4_5_tarjetas_estimada"] = round(100.0 / prob_over_4_5_cards, 2) if prob_over_4_5_cards > 5 else 1.90
            if "cuota_under_4_5_tarjetas_estimada" not in market_data:
                market_data["cuota_under_4_5_tarjetas_estimada"] = round(100.0 / (100.0 - prob_over_4_5_cards), 2) if prob_over_4_5_cards < 95 else 1.90
        except Exception as e:
            print(f"[MarketAnalyzer] Error cargando o validando JSON del mercado: {e}. Respuesta cruda: {raw_response}")
            
            # Calcular cuotas justas simuladas dinámicamente para el fallback
            c_local = round(100.0 / prob_local, 2) if prob_local > 5 else 15.0
            c_visitor = round(100.0 / prob_visitor, 2) if prob_visitor > 5 else 15.0
            c_draw = round(100.0 / prob_draw, 2) if prob_draw > 5 else 8.0
            
            diff_prob = prob_local - prob_visitor
            if diff_prob > 40:
                h_line = f"{local_team} -1.5"
                h_pick = f"{local_team} -1.5"
            elif diff_prob > 15:
                h_line = f"{local_team} -0.5"
                h_pick = f"{local_team} -0.5"
            elif diff_prob < -40:
                h_line = f"{visitor_team} -1.5"
                h_pick = f"{visitor_team} -1.5"
            elif diff_prob < -15:
                h_line = f"{visitor_team} -0.5"
                h_pick = f"{visitor_team} -0.5"
            else:
                h_line = f"{local_team} +0.0"
                h_pick = "Hándicap Asiático +0.0"
                
            c_over = round(100.0 / prob_over_2_5, 2) if prob_over_2_5 > 5 else 2.5
            c_under = round(100.0 / (100.0 - prob_over_2_5), 2) if prob_over_2_5 < 95 else 2.5
            
            # Cuotas justas para corners
            c_over_corners = round(100.0 / prob_over_9_5_corners, 2) if prob_over_9_5_corners > 5 else 1.90
            c_under_corners = round(100.0 / (100.0 - prob_over_9_5_corners), 2) if prob_over_9_5_corners < 95 else 1.90
            
            # Cuotas justas para tarjetas
            c_over_cards = round(100.0 / prob_over_4_5_cards, 2) if prob_over_4_5_cards > 5 else 1.90
            c_under_cards = round(100.0 / (100.0 - prob_over_4_5_cards), 2) if prob_over_4_5_cards < 95 else 1.90
            
            market_data = {
                "cuota_local_estimada": c_local,
                "cuota_empate_estimada": c_draw,
                "cuota_visitante_estimada": c_visitor,
                "handicap_asiatico_linea": h_line,
                "handicap_asiatico_cuota": 1.85,
                "cuota_over_2_5_estimada": c_over,
                "cuota_under_2_5_estimada": c_under,
                "cuota_over_9_5_corners_estimada": c_over_corners,
                "cuota_under_9_5_corners_estimada": c_under_corners,
                "cuota_over_4_5_tarjetas_estimada": c_over_cards,
                "cuota_under_4_5_tarjetas_estimada": c_under_cards,
                "comparativa_valor": [
                    f"Cálculo matemático fallback: Probabilidad Local de {prob_local:.1f}% implica cuota justa de {c_local}.",
                    f"Probabilidad de Over 9.5 Corners de {prob_over_9_5_corners:.1f}% implica cuota justa de {c_over_corners}."
                ],
                "recomendacion_apuesta": f"Apuesta de valor teórica: {h_pick} o Más de 1.5 goles"
            }

        # Consolidar todas las estadísticas e información de mercado
        stats_and_market = {
            "estadisticas_simuladas": {
                "probabilidad_local_porcentaje": prob_local,
                "probabilidad_visitante_porcentaje": prob_visitor,
                "probabilidad_empate_porcentaje": prob_draw,
                "probabilidad_over_1_5_porcentaje": prob_over_1_5,
                "probabilidad_over_2_5_porcentaje": prob_over_2_5,
                "probabilidad_over_8_5_corners_porcentaje": prob_over_8_5_corners,
                "probabilidad_over_9_5_corners_porcentaje": prob_over_9_5_corners,
                "probabilidad_over_10_5_corners_porcentaje": prob_over_10_5_corners,
                "probabilidad_over_3_5_tarjetas_porcentaje": prob_over_3_5_cards,
                "probabilidad_over_4_5_tarjetas_porcentaje": prob_over_4_5_cards,
                "probabilidad_over_5_5_tarjetas_porcentaje": prob_over_5_5_cards,
                "promedio_goles_local": avg_goals_local,
                "promedio_goles_visitante": avg_goals_visitor,
                "promedio_tiros_esquina_local": avg_corners_local,
                "promedio_tiros_esquina_visitante": avg_corners_visitor,
                "promedio_tarjetas_amarillas": avg_yellow_cards,
                "promedio_tarjetas_rojas": avg_red_cards
            },
            "datos_mercado": market_data
        }

        return stats_and_market
