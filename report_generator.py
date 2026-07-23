import json

class ReportGenerator:
    def __init__(self, gemini_client=None):
        self.gemini_client = gemini_client

    def generate_report(self, local_team: str, visitor_team: str, raw_data: dict, tactics: dict, simulations: list, market_analysis: dict, environment: dict = None) -> str:
        """
        Genera el informe de pronóstico final utilizando el motor SBIE v2.0 (Sports Betting Intelligence Engine).
        """
        if not environment:
            environment = {}

        # Formatear la lista de simulaciones para el reporte
        sims_summary = ""
        for s in simulations:
            g_l = s.get("goles_local", 0)
            g_v = s.get("goles_visitante", 0)
            esc = s.get("escenario", "Estándar")
            pos_l = s.get("posesion_local_porcentaje", 50)
            pos_v = 100 - pos_l
            
            sims_summary += f"""
* **Simulación {s.get('simulacion_id')}: {esc}** | Resultado: {local_team} {g_l} - {g_v} {visitor_team} | Posesión: {pos_l}% - {pos_v}% | Corners: {s.get('tiros_esquina_local', 5)} - {s.get('tiros_esquina_visitante', 4)}
"""

        if not market_analysis:
            market_analysis = {}
        stats = market_analysis.get("estadisticas_simuladas", {}) or {}
        market = market_analysis.get("datos_mercado", {}) or {}

        # Saneamiento de valores estadísticos
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

        # Si tenemos GeminiClient, realizamos la síntesis con la metodología SBIE v2.0
        if self.gemini_client:
            sbie_prompt = f"""
Eres SBIE (Sports Betting Intelligence Engine v2.0) operando en ROM LUDOPATA.
Genera el informe ejecutivo de análisis probabilístico para el partido: {local_team.upper()} vs {visitor_team.upper()}.

DATOS DE ENTRADA DISPONIBLES:
1. Análisis Táctico y Alineaciones:
   - Formación Local: {tactics.get('local_formacion', 'Por confirmar')} | Estilo: {tactics.get('local_estilo')}
   - Formación Visitante: {tactics.get('visitante_formacion', 'Por confirmar')} | Estilo: {tactics.get('visitante_estilo')}
   - Enfrentamiento: {tactics.get('analisis_enfrentamiento')}
   - Zonas Clave: {tactics.get('zonas_clave')}
   - Alineaciones Oficiales: {tactics.get('alineaciones_oficiales')} ({tactics.get('advertencia_lineas', '')})

2. Entorno, Árbitro y Estadio:
   - Árbitro Designado: {environment.get('arbitro_nombre', 'Desconocido')}
   - Trayectoria / Estilo Árbitro: {environment.get('arbitro_estilo', 'Información no especificada.')}
   - Árbitro Tarjetero: {environment.get('arbitro_tarjetero', 'No')} | Promedio Tarjetas: {environment.get('arbitro_promedio_tarjetas', 'N/A')}
   - Estadio: {environment.get('estadio_nombre', 'Desconocido')} | Césped: {environment.get('estadio_cesped', 'Natural')}
   - Impacto de Localía: {environment.get('estadio_localia_impacto', 'Normal')}
   - Clima: {environment.get('clima_pronostico', 'Despejado / Clima estándar')}
   - Noticias / Rumores: {raw_data.get('player_rumors', ['Sin noticias destacadas'])[0] if raw_data.get('player_rumors') else 'Sin noticias'}

3. Probabilidades de Monte Carlo (10,000 corridas):
   - Victoria Local: {stats.get('probabilidad_local_porcentaje', 33.3):.1f}% | Empate: {stats.get('probabilidad_empate_porcentaje', 33.3):.1f}% | Victoria Visitante: {stats.get('probabilidad_visitante_porcentaje', 33.3):.1f}%
   - Over 1.5 Goles: {stats.get('probabilidad_over_1_5_porcentaje', 50):.1f}% | Over 2.5 Goles: {stats.get('probabilidad_over_2_5_porcentaje', 50):.1f}%
   - Corners: Local {stats.get('promedio_tiros_esquina_local', 5.0):.1f} | Visitante {stats.get('promedio_tiros_esquina_visitante', 4.0):.1f} | Over 9.5: {stats.get('probabilidad_over_9_5_corners_porcentaje', 40.0):.1f}%
   - Disciplina: {stats.get('promedio_tarjetas_amarillas', 4.0):.1f} Amarillas | Over 4.5 Tarjetas: {stats.get('probabilidad_over_4_5_tarjetas_porcentaje', 50.0):.1f}%

4. Mercado y Cuotas Estimadas:
   - Cuotas 1X2: Local {market.get('cuota_local_estimada', 'N/A')} | Empate {market.get('cuota_empate_estimada', 'N/A')} | Visitante {market.get('cuota_visitante_estimada', 'N/A')}
   - Pick de Referencia: {market.get('recomendacion_apuesta', 'Sin pronóstico')}

Sigue estrictamente la estructura SBIE v2.0 (13 Fases) en formato GitHub Markdown limpio en español:
1. Resumen Ejecutivo
2. Calidad de los Datos (%) y Validación
3. Informe del Comité de Analistas (Estadístico, Táctico, Plantilla, Psicológico, Mercado, Córners, Riesgo)
4. Contexto del Árbitro, Estadio y Clima
5. Objeciones del Auditor del Diablo (¿Por qué podría fallar?)
6. Detector de Contradicciones y Ponderación Dinámica
7. Estimación de Probabilidades y Mercados Analizados
8. Evaluación de Valor Esperado (+EV) y Mercados a Evitar
9. Análisis Específico de Córners (Tiros de Esquina) y Disciplina
10. Stake Sugerido (0 a 5) y Nivel de Confianza Objetiva
11. Conclusión Final y Pick Recomendado
"""
            sbie_system_instruction = """
Eres SBIE (Sports Betting Intelligence Engine v2.0). No eres un tipster ni haces apuestas impulsivas. Tu objetivo es realizar un análisis probabilístico objetivo sustentado únicamente en la evidencia. Incluye explícitamente la sección del Árbitro y Estadio con sus datos. Responde en español en formato Markdown limpio.
"""
            try:
                sbie_report = self.gemini_client.generate_content(sbie_prompt, system_instruction=sbie_system_instruction)
                if sbie_report and len(sbie_report) > 200:
                    return sbie_report
            except Exception as e:
                print(f"[ReportGenerator] Advertencia al generar reporte SBIE v2.0 con Gemini ({e}). Usando plantilla local.")

        # Fallback a plantilla estática estructurada si Gemini no responde
        report = f"""# ANÁLISIS SBIE v2.0 (SPORTS BETTING INTELLIGENCE ENGINE): {local_team.upper()} vs {visitor_team.upper()}

---

## 1. Resumen Ejecutivo
Análisis probabilístico realizado mediante el modelo cuantitativo Monte Carlo y evaluación multi-analista para {local_team} vs {visitor_team}.

## 2. Calidad de los Datos
*   **Estado de Alineaciones:** {tactics.get('advertencia_lineas') or 'Confirmadas en Vivo.'}
*   **Porcentaje de Calidad Estimado:** {'80% - Datos completos' if tactics.get('alineaciones_oficiales') else '60% - Alineación por confirmar'}

## 3. Contexto del Árbitro, Estadio y Clima
*   **Árbitro Designado:** {environment.get('arbitro_nombre', 'Desconocido')}
    *   *Trayectoria y Rigurosidad:* {environment.get('arbitro_estilo', 'Información no especificada.')}
    *   *Tarjetero:* {environment.get('arbitro_tarjetero', 'No')} | *Promedio:* {environment.get('arbitro_promedio_tarjetas', 'N/A')}
*   **Estadio:** {environment.get('estadio_nombre', 'Desconocido')} (Césped: {environment.get('estadio_cesped', 'Natural')})
    *   *Impacto de Localía:* {environment.get('estadio_localia_impacto', 'Normal')}
*   **Clima:** {environment.get('clima_pronostico', 'Despejado / Clima estándar')}

## 4. Análisis Táctico y de Campo
*   **{local_team} ({tactics.get('local_formacion', '4-3-3')}):** {tactics.get('local_estilo', 'Estilo no definido.')}
*   **{visitor_team} ({tactics.get('visitante_formacion', '4-2-3-1')}):** {tactics.get('visitante_estilo', 'Estilo no definido.')}
*   **Enfrentamiento:** {tactics.get('analisis_enfrentamiento', 'Sin detalles.')}

## 5. Probabilidades Estimadas (Monte Carlo 10,000 Corridas)
*   **Victoria Local ({local_team}):** {stats.get('probabilidad_local_porcentaje', 33.3):.1f}%
*   **Empate:** {stats.get('probabilidad_empate_porcentaje', 33.3):.1f}%
*   **Victoria Visitante ({visitor_team}):** {stats.get('probabilidad_visitante_porcentaje', 33.3):.1f}%
*   **Over 2.5 Goles:** {stats.get('probabilidad_over_2_5_porcentaje', 50):.1f}%
*   **Over 9.5 Corners:** {stats.get('probabilidad_over_9_5_corners_porcentaje', 40.0):.1f}%
*   **Over 4.5 Tarjetas:** {stats.get('probabilidad_over_4_5_tarjetas_porcentaje', 50.0):.1f}%

## 6. Recomendación y Gestión del Riesgo (SBIE v2.0)
> [!IMPORTANT]
> **Pick de Valor:** {market.get('recomendacion_apuesta', 'Sin pronóstico definitivo.')}
> **Stake Sugerido:** {1.5 if tactics.get('alineaciones_oficiales') else 0.5} / 5 (Gestión de Banca Conservadora)
"""
        return report

