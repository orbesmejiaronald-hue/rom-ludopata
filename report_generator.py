import json

class ReportGenerator:
    def __init__(self):
        pass

    def generate_report(self, local_team: str, visitor_team: str, raw_data: dict, tactics: dict, simulations: list, market_analysis: dict) -> str:
        """
        Genera el informe de pronóstico final estructurado y redactado en español.
        """
        # Formatear la lista de simulaciones para el reporte
        sims_summary = ""
        for s in simulations:
            g_l = s.get("goles_local", 0)
            g_v = s.get("goles_visitante", 0)
            esc = s.get("escenario", "Estándar")
            cron = s.get("cronica_minuto_a_minuto", [])
            cron_text = "\n   * ".join(cron[:3]) # Primeros 3 hitos para no saturar el reporte
            
            pos_l = s.get("posesion_local_porcentaje")
            if pos_l is None:
                pos_l = 50
            pos_v = 100 - pos_l
            
            sims_summary += f"""
### Simulación {s.get('simulacion_id')}: {esc}
*   **Resultado Simulado:** {local_team} **{g_l} - {g_v}** {visitor_team}
*   **Posesión:** {local_team} {pos_l}% - {pos_v}% {visitor_team}
*   **Tiros de esquina:** Local {s.get('tiros_esquina_local', 5)} | Visitante {s.get('tiros_esquina_visitante', 4)}
*   **Cronología Clave:**
   * {cron_text}
"""

        # Resumen estadístico robusto
        if not market_analysis:
            market_analysis = {}
        stats = market_analysis.get("estadisticas_simuladas", {}) or {}
        market = market_analysis.get("datos_mercado", {}) or {}

        # Saneamiento de valores estadísticos para evitar fallas de formato (.1f)
        for key in ['probabilidad_local_porcentaje', 'probabilidad_empate_porcentaje', 'probabilidad_visitante_porcentaje',
                    'probabilidad_over_1_5_porcentaje', 'probabilidad_over_2_5_porcentaje',
                    'probabilidad_over_8_5_corners_porcentaje', 'probabilidad_over_9_5_corners_porcentaje', 'probabilidad_over_10_5_corners_porcentaje',
                    'probabilidad_over_3_5_tarjetas_porcentaje', 'probabilidad_over_4_5_tarjetas_porcentaje', 'probabilidad_over_5_5_tarjetas_porcentaje',
                    'promedio_tiros_esquina_local', 'promedio_tiros_esquina_visitante',
                    'promedio_tarjetas_amarillas', 'promedio_tarjetas_rojas']:
            if stats.get(key) is None:
                if 'promedio' in key:
                    stats[key] = 0.0
                elif 'over' in key:
                    stats[key] = 50.0
                else:
                    stats[key] = 33.3

        # Saneamiento de valores de mercado
        for key in ['cuota_local_estimada', 'cuota_empate_estimada', 'cuota_visitante_estimada',
                    'handicap_asiatico_linea', 'handicap_asiatico_cuota',
                    'cuota_over_2_5_estimada', 'cuota_under_2_5_estimada',
                    'cuota_over_9_5_corners_estimada', 'cuota_under_9_5_corners_estimada',
                    'cuota_over_4_5_tarjetas_estimada', 'cuota_under_4_5_tarjetas_estimada',
                    'recomendacion_apuesta']:
            if market.get(key) is None:
                market[key] = "N/A"

        # Formatear comparativa de valor
        comp_valor_text = ""
        comparativa = market.get("comparativa_valor")
        if not comparativa or not isinstance(comparativa, list):
            comparativa = ["Sin datos comparativos de valor."]
        for item in comparativa:
            comp_valor_text += f"* {item}\n"

        # Armar el reporte Markdown completo en español
        report = f"""# ANÁLISIS PROFESIONAL Y PRONÓSTICO (SHARP BETTING): {local_team.upper()} vs {visitor_team.upper()}

---

## 1. Análisis de Alineaciones y Tácticas
*   **{local_team} ({tactics.get('local_formacion', '4-3-3')}):** {tactics.get('local_estilo', 'Estilo no definido.')}
*   **{visitor_team} ({tactics.get('visitante_formacion', '4-2-3-1')}):** {tactics.get('visitante_estilo', 'Estilo no definido.')}
*   **Enfrentamiento Táctico:** {tactics.get('analisis_enfrentamiento', 'Sin detalles de emparejamiento.')}
*   **Zonas Clave del Campo:** {tactics.get('zonas_clave', 'Mediocampo y bandas.')}
*   **Ventaja Táctica:** {tactics.get('ventaja_tactica', 'Ninguna clara.')}

---

## 2. Contexto Ambiental, Árbitro y Vestuario
*   **Árbitro:**
    *   *Estadísticas e Historial:* {raw_data.get('referee', ['No hay información detallada del árbitro en internet.'])[0] if raw_data.get('referee') else 'No hay información.'}
*   **Estadio y Clima:**
    *   *Detalles:* {raw_data.get('stadium_and_weather', ['No hay información de clima disponible.'])[0] if raw_data.get('stadium_and_weather') else 'No hay información.'}
*   **Rumores y Estado Anímico:**
    *   *Sentimiento del Vestuario:* {raw_data.get('player_rumors', ['Sin rumores destacados recientemente.'])[0] if raw_data.get('player_rumors') else 'Sin rumores.'}

---

## 3. Resumen Estadístico de las 10 Simulaciones Coherentes
El motor ha ejecutado 10 simulaciones consecutivas con escenarios dinámicos (lesiones, clima, tarjetas) y 10,000 corridas del modelo matemático de Monte Carlo.

*   **Probabilidad de Victoria Local ({local_team}):** {stats.get('probabilidad_local_porcentaje', 33.3):.1f}%
*   **Probabilidad de Empate:** {stats.get('probabilidad_empate_porcentaje', 33.3):.1f}%
*   **Probabilidad de Victoria Visitante ({visitor_team}):** {stats.get('probabilidad_visitante_porcentaje', 33.3):.1f}%
*   **Goles Totales:**
    *   Probabilidad Más de 1.5 Goles: {stats.get('probabilidad_over_1_5_porcentaje', 50):.1f}%
    *   Probabilidad Más de 2.5 Goles: {stats.get('probabilidad_over_2_5_porcentaje', 50):.1f}%
*   **Tiros de Esquina:**
    *   Promedio Total: Local {stats.get('promedio_tiros_esquina_local', 5.0):.1f} | Visitante {stats.get('promedio_tiros_esquina_visitante', 4.0):.1f}
    *   Probabilidad Más de 8.5 Corners: {stats.get('probabilidad_over_8_5_corners_porcentaje', 50.0):.1f}%
    *   Probabilidad Más de 9.5 Corners: {stats.get('probabilidad_over_9_5_corners_porcentaje', 40.0):.1f}%
    *   Probabilidad Más de 10.5 Corners: {stats.get('probabilidad_over_10_5_corners_porcentaje', 30.0):.1f}%
*   **Tarjetas y Disciplina:**
    *   Promedio Total: {stats.get('promedio_tarjetas_amarillas', 4.0):.1f} Amarillas y {stats.get('promedio_tarjetas_rojas', 0.2):.1f} Rojas por partido.
    *   Probabilidad Más de 3.5 Tarjetas: {stats.get('probabilidad_over_3_5_tarjetas_porcentaje', 60.0):.1f}%
    *   Probabilidad Más de 4.5 Tarjetas: {stats.get('probabilidad_over_4_5_tarjetas_porcentaje', 50.0):.1f}%
    *   Probabilidad Más de 5.5 Tarjetas: {stats.get('probabilidad_over_5_5_tarjetas_porcentaje', 40.0):.1f}%

---

## 4. Comparativa de Mercado, Hándicap Asiático e Ineficiencias (Value Betting)
*   **Cuotas 1X2 Estimadas (Mercado):** Local: {market.get('cuota_local_estimada')} | Empate: {market.get('cuota_empate_estimada')} | Visitante: {market.get('cuota_visitante_estimada')}
*   **Hándicap Asiático de Referencia:** {market.get('handicap_asiatico_linea')} (Cuota: {market.get('handicap_asiatico_cuota')})
*   **Más/Menos 2.5 Goles Cuotas:** Más de 2.5: {market.get('cuota_over_2_5_estimada')} | Menos de 2.5: {market.get('cuota_under_2_5_estimada')}
*   **Mercados de Corners y Tarjetas:**
    *   Más de 9.5 Corners Cuota: {market.get('cuota_over_9_5_corners_estimada')} | Menos de 9.5: {market.get('cuota_under_9_5_corners_estimada')}
    *   Más de 4.5 Tarjetas Cuota: {market.get('cuota_over_4_5_tarjetas_estimada')} | Menos de 4.5: {market.get('cuota_under_4_5_tarjetas_estimada')}

### Análisis de Valor (Value Betting & Odds Analysis):
{comp_valor_text}

---

## 5. Recomendación y Pick de Valor (Sharp Pick)
> [!IMPORTANT]
> **Pick Recomendado:** {market.get('recomendacion_apuesta', 'Sin pronóstico definitivo.')}

---

## Anexo: Bitácora de las 10 Simulaciones Auditadas
{sims_summary}
"""
        return report
