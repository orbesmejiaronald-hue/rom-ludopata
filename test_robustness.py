import json
import sys
from simulation_engine import SimulationEngine

class MockGeminiCorrupt:
    def __init__(self):
        self.client_type = "mock"
        self.call_count = 0

    def generate_content(self, prompt: str, system_instruction: str = None) -> str:
        self.call_count += 1
        
        # En el caso de validación, siempre retornar que es válido para simplificar
        if "inconsistencias lógicas" in prompt or "inspector" in prompt or "Analiza la siguiente simulación" in prompt:
            return json.dumps({"es_valido": True, "motivo_rechazo": ""})
            
        # En el primer intento de simulación, devolver JSON corrupto (con un error de sintaxis)
        if self.call_count == 1:
            print("[TestRobustness] Mocking JSON malformado (intento 1)...")
            return "{ 'simulacion_id': 1, 'escenario': 'Roto', goles_local: 2, goles_visitante: }"  # Error de sintaxis JSON
            
        # En el segundo intento, devolver un JSON válido
        print("[TestRobustness] Mocking JSON válido (intento 2)...")
        return json.dumps({
            "simulacion_id": 1,
            "escenario": "Recuperado",
            "goles_local": 2,
            "goles_visitante": 1,
            "anotadores": [
                {"minuto": 20, "jugador": "L. Messi", "equipo": "local"},
                {"minuto": 50, "jugador": "K. Mbappé", "equipo": "visitante"},
                {"minuto": 80, "jugador": "L. Martínez", "equipo": "local"}
            ],
            "tarjetas_amarillas": [],
            "tarjetas_rojas": [],
            "tiros_esquina_local": 5,
            "tiros_esquina_visitante": 5,
            "posesion_local_porcentaje": 50,
            "cronica_minuto_a_minuto": ["Minuto 90: Fin."]
        })

def test_json_recovery():
    print("[TestRobustness] Iniciando prueba de recuperación de JSON...")
    mock_client = MockGeminiCorrupt()
    engine = SimulationEngine(mock_client)
    
    # Ejecutar una simulación del partido
    sims = engine.run_all_simulations(
        "Argentina", "Francia", 
        data_context={"referee": [], "stadium_and_weather": [], "player_rumors": []}, 
        tactical_analysis={"local_formacion": "4-3-3", "local_estilo": "Posición", "visitante_formacion": "4-2-3-1", "visitante_estilo": "Contra"}
    )
    
    # Comprobar si se completaron las simulaciones y la primera se recuperó del error de formato
    first_sim = sims[0]
    print(f"[TestRobustness] Nombre del escenario simulado 1: {first_sim.get('escenario')}")
    print(f"[TestRobustness] Marcador local: {first_sim.get('goles_local')} | Marcador visitante: {first_sim.get('goles_visitante')}")
    
    if first_sim.get("escenario") == "Recuperado":
        print("[TestRobustness] ¡ÉXITO! El motor se recuperó correctamente del JSON malformado y generó la simulación correcta.")
        return True
    else:
        print("[TestRobustness] ¡FALLO! El motor no pudo recuperarse o utilizó un fallback incorrecto.")
        return False

if __name__ == "__main__":
    success = test_json_recovery()
    sys.exit(0 if success else 1)
