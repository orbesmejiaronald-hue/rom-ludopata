import sys
import os

# Añadir el directorio actual al path por si acaso
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agent_coordinator import AgentCoordinator

def main():
    coordinator = AgentCoordinator()
    
    local = "México"
    visitor = "República Checa"
    
    print("[CustomRunner] Recopilando otros datos y sobreescribiendo alineaciones...")
    raw_data = coordinator.collector.collect_all_data(local, visitor)
    
    # Inyectar las alineaciones oficiales que confirmamos en vivo
    raw_data["lineups"] = [
        "México alineación titular confirmada hoy: Rangel (GK); Sánchez, Reyes, Montes, Chávez; Mora, Romo, Álvarez (C); Alvarado, Martínez, Quiñones.",
        "República Checa alineación titular confirmada hoy: Kovář (GK); Hranáč, Holeš, Krejčí (C); Doudera, Červ, Sadilek, Coufal; Višinský, Šulc; Hložek."
    ]
    
    # Correr el análisis táctico
    print("[CustomRunner] Analizando tácticas...")
    tactics = coordinator.tactical_analyzer.analyze_tactics(local, visitor, raw_data["lineups"])
    
    # Correr las 10 simulaciones
    print("[CustomRunner] Corriendo 10 simulaciones con incidentes lógicos...")
    simulations = coordinator.sim_engine.run_all_simulations(local, visitor, raw_data, tactics)
    
    # Analizar mercado y valor
    print("[CustomRunner] Analizando cuotas y valor...")
    market_analysis = coordinator.market_analyzer.analyze_market_and_stats(local, visitor, simulations, raw_data)
    
    # Guardar en el historial estructurado local
    coordinator._save_to_history(local, visitor, tactics, simulations, market_analysis)
    
    # Generar reporte final
    print("[CustomRunner] Generando el reporte final...")
    report = coordinator.report_generator.generate_report(local, visitor, raw_data, tactics, simulations, market_analysis)
    
    output_path = "pronostico_resultado.md"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(report)
        
    print(f"[CustomRunner] ¡Reporte generado con éxito en: {output_path}!")

if __name__ == "__main__":
    main()
