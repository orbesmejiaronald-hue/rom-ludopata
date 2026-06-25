import json
from gemini_client import GeminiClient

class TacticalAnalyzer:
    def __init__(self, gemini_client: GeminiClient):
        self.client = gemini_client

    def analyze_tactics(self, local_team: str, visitor_team: str, lineups_data: list) -> dict:
        """
        Analiza las alineaciones y esquemas tácticos de ambos equipos usando Gemini.
        """
        print(f"[TacticalAnalyzer] Analizando alineaciones y tácticas para {local_team} vs {visitor_team}...")
        
        lineups_text = "\n".join(lineups_data) if lineups_data else "No se encontraron datos explícitos de alineaciones."
        
        prompt = f"""
Analiza las alineaciones, esquemas tácticos y parado de los equipos para el siguiente partido de fútbol:
Local: {local_team}
Visitante: {visitor_team}

Información recopilada de internet en tiempo real:
{lineups_text}

Tu tarea es:
1. Identificar la alineación o formación titular de cada equipo. 
   - Si la información indica "ESTADO DE ALINEACIONES: CONFIRMADAS EN VIVO", extrae la alineación oficial confirmada de hoy.
   - Si la información indica "ESTADO DE ALINEACIONES: NO CONFIRMADAS EN VIVO", NO te detengas. Extrae la alineación utilizada en el último partido reciente de cada equipo o la alineación probable típica a partir del texto y las noticias provistas.
2. Definir cómo se desarrollará el parado táctico y estilo de juego.
3. Comparar ambos esquemas e identificar qué equipo tiene ventaja táctica y en qué zonas del campo.

Devuelve tu respuesta únicamente en un formato JSON estructurado como el siguiente, sin formato markdown ```json adicional (solo el texto JSON puro para que pueda ser cargado con json.loads en Python):
{{
  "local_formacion": "formación ej. 4-3-3",
  "local_estilo": "descripción breve del estilo de juego",
  "visitante_formacion": "formación ej. 4-2-3-1",
  "visitante_estilo": "descripción breve del estilo de juego",
  "analisis_enfrentamiento": "cómo interactúan los dos parados tácticos y qué podemos esperar",
  "zonas_clave": "zonas del campo críticas donde se decidirá el partido",
  "ventaja_tactica": "cuál equipo se beneficia tácticamente del emparejamiento y por qué",
  "alineaciones_oficiales": true, // Pon true si el estado indica CONFIRMADAS EN VIVO, o false si indica NO CONFIRMADAS EN VIVO (de referencia/último partido)
  "advertencia_lineas": "⚠️ ADVERTENCIA: Alineaciones oficiales no confirmadas en vivo. Basado en el último partido de cada equipo." // Deja esta advertencia en español si no son confirmadas oficiales hoy (alineaciones_oficiales es false), de lo contrario deja una cadena vacía ""
}}
"""

        system_instruction = "Eres un analista táctico de fútbol profesional de nivel élite, extremadamente riguroso y obsesionado con los datos reales. Si la alineación oficial no está confirmada hoy, extrae la del último partido de referencia a partir de los textos provistos."
        
        raw_response = self.client.generate_content(prompt, system_instruction=system_instruction)
        
        # Limpiar posibles bloques markdown del JSON
        clean_response = raw_response.strip()
        if clean_response.startswith("```"):
            lines = clean_response.splitlines()
            if lines[0].startswith("```json") or lines[0].startswith("```"):
                clean_response = "\n".join(lines[1:-1])
        
        try:
            analysis = json.loads(clean_response)
            # Asegurar claves de oficialidad en el retorno
            if "alineaciones_oficiales" not in analysis:
                analysis["alineaciones_oficiales"] = "CONFIRMADAS EN VIVO" in lineups_text
            if "advertencia_lineas" not in analysis:
                analysis["advertencia_lineas"] = "" if analysis["alineaciones_oficiales"] else "⚠️ ADVERTENCIA: Alineaciones oficiales no confirmadas en vivo. Basado en el último partido de cada equipo."
            return analysis
        except Exception as e:
            print(f"[TacticalAnalyzer] Error decodificando JSON: {e}. Respuesta cruda: {raw_response}")
            # Fallback en caso de error de parseo
            return {
                "local_formacion": "No determinada",
                "local_estilo": "Estilo estándar",
                "visitante_formacion": "No determinada",
                "visitante_estilo": "Estilo estándar",
                "analisis_enfrentamiento": "Análisis táctico no disponible por error de formato.",
                "zonas_clave": "Mediocampo",
                "ventaja_tactica": "Ninguna clara debido a falta de datos tácticos",
                "alineaciones_oficiales": False,
                "advertencia_lineas": "⚠️ ADVERTENCIA: Alineaciones oficiales no confirmadas en vivo. Basado en el último partido."
            }
