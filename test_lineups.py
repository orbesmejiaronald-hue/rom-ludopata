import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from gemini_client import GeminiClient
from simulation_engine import SimulationEngine

def test_lineup_adjustments():
    print("[TestLineups] Iniciando prueba de ajuste por alineación...")
    
    client = GeminiClient()
    engine = SimulationEngine(client)
    
    # Caso 1: Alineación titular súper fuerte (Gala)
    lineups_gala = [
        "Real Madrid alineación titular confirmada hoy: Courtois (GK); Carvajal, Militão, Rüdiger, Mendy; Valverde, Tchouaméni, Bellingham (C); Rodrygo, Mbappé, Vini Jr.",
        "Barcelona alineación titular confirmada hoy: Ter Stegen (GK); Koundé, Araújo, Christensen, Balde; De Jong, Pedri, Gavi; Raphinha, Lewandowski, Lamine Yamal."
    ]
    
    # Caso 2: Alineación titular suplente/juvenil (Debilitada)
    lineups_suplente = [
        "Real Madrid alineación titular confirmada hoy: Lunin (GK); Lucas Vázquez, Vallejo, Jacobo Ramón, Fran García; Ceballos, Modrić (C), Arda Güler; Endrick, Brahim Díaz, Nico Paz.",
        "Barcelona alineación titular confirmada hoy: Ter Stegen (GK); Koundé, Araújo, Christensen, Balde; De Jong, Pedri, Gavi; Raphinha, Lewandowski, Lamine Yamal."
    ]
    
    # Calcular ajustes
    adj_gala = engine._calculate_lineup_adjustment("Real Madrid", "Barcelona", lineups_gala)
    adj_suplente = engine._calculate_lineup_adjustment("Real Madrid", "Barcelona", lineups_suplente)
    
    print("\n--- Resultados de Ajuste de Alineación ---")
    print(f"Alineación de Gala de Real Madrid:")
    print(f"  * Jugadores extraídos: {adj_gala['local_players_count']}")
    print(f"  * Factor de ataque: {adj_gala['f_attack_local']:.4f}")
    print(f"  * Factor de defensa: {adj_gala['f_defense_local']:.4f}")
    
    print(f"Alineación Suplente de Real Madrid:")
    print(f"  * Jugadores extraídos: {adj_suplente['local_players_count']}")
    print(f"  * Factor de ataque: {adj_suplente['f_attack_local']:.4f}")
    print(f"  * Factor de defensa: {adj_suplente['f_defense_local']:.4f}")
    
    # Aserciones
    assert adj_gala["f_attack_local"] > adj_suplente["f_attack_local"], \
        f"Fallo: El factor ofensivo de la gala ({adj_gala['f_attack_local']:.4f}) debería ser mayor al suplente ({adj_suplente['f_attack_local']:.4f})"
        
    print("\n[TestLineups] ¡ÉXITO! Las aseveraciones tácticas y la carga de perfiles de jugadores pasaron.")

if __name__ == "__main__":
    test_lineup_adjustments()
