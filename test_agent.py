import os
import sys

def test_imports():
    print("[TestAgent] Probando importaciones de los módulos...")
    try:
        from data_collector import DataCollector
        from tactical_analyzer import TacticalAnalyzer
        from simulation_engine import SimulationEngine
        from market_analyzer import MarketAnalyzer
        from report_generator import ReportGenerator
        from agent_coordinator import AgentCoordinator
        print("[TestAgent] ¡Importaciones exitosas!")
        return True
    except Exception as e:
        print(f"[TestAgent] ERROR de importación: {e}")
        return False

def test_data_collector():
    print("\n[TestAgent] Probando DataCollector con DuckDuckGo...")
    try:
        from data_collector import DataCollector
        collector = DataCollector()
        res = collector.search_duckduckgo("Real Madrid", max_results=2)
        print(f"[TestAgent] Encontrados {len(res)} resultados para 'Real Madrid':")
        for item in res:
            print(f" - {item['url']} (snippet: {item['snippet'][:80]}...)")
        return len(res) > 0
    except Exception as e:
        print(f"[TestAgent] ERROR en DataCollector: {e}")
        return False

if __name__ == "__main__":
    print("=== INICIANDO PRUEBAS UNITARIAS DE INTEGRACIÓN ===")
    imports_ok = test_imports()
    if not imports_ok:
        sys.exit(1)
        
    collector_ok = test_data_collector()
    if not collector_ok:
        print("[TestAgent] ADVERTENCIA: DataCollector falló. Puede deberse a falta de red o cambios de DuckDuckGo.")
    
    print("\n=== PRUEBAS FINALIZADAS ===")
