import os
import json
import math
from datetime import datetime
from dixon_coles import DixonColesModel

def run_backtest(matches, division_filter=None, initial_bankroll=1000.0, min_edge=0.06, kelly_fraction=0.15, retrain_every=40):
    """
    Ejecuta un backtesting retrospectivo usando Dixon-Coles y el Criterio de Kelly.
    """
    # Filtrar por división si se solicita
    if division_filter:
        div_matches = [m for m in matches if m["div"] == division_filter]
    else:
        div_matches = matches
        
    if len(div_matches) < 200:
        print(f"[Backtester] Advertencia: Muy pocos partidos ({len(div_matches)}) para un backtesting confiable.")
        return None
        
    print(f"\n[Backtester] === INICIANDO BACKTEST: {division_filter or 'TODAS'} ===")
    print(f"[Backtester] Partidos totales: {len(div_matches)} | Banca inicial: ${initial_bankroll:.2f} USD")
    print(f"[Backtester] Edge mínimo: {min_edge*100:.1f}% | Fracción de Kelly: {kelly_fraction:.2f} | Frecuencia reentrenamiento: cada {retrain_every} partidos")
    
    bankroll = initial_bankroll
    peak_bankroll = bankroll
    max_drawdown = 0.0
    
    total_bets = 0
    bets_won = 0
    total_staked = 0.0
    total_returned = 0.0
    
    # Empezar a apostar después del primer 35% de partidos (ventana de calentamiento)
    warmup_index = int(len(div_matches) * 0.35)
    print(f"[Backtester] Ventana de calentamiento: {warmup_index} partidos. Las apuestas inician en el partido {warmup_index + 1}.")
    
    dc_model = None
    bet_history = []
    
    for idx in range(warmup_index, len(div_matches)):
        match = div_matches[idx]
        home = match["home"]
        away = match["away"]
        
        # Reentrenar el modelo Dixon-Coles de forma periódica con todos los partidos del pasado
        if dc_model is None or (idx - warmup_index) % retrain_every == 0:
            past_matches = div_matches[:idx]
            
            # Recalcular 'days_ago' relativo a la fecha del partido actual
            current_match_date = datetime.strptime(match["date"], "%Y-%m-%d")
            training_data = []
            for pm in past_matches:
                pm_date = datetime.strptime(pm["date"], "%Y-%m-%d")
                days_ago = (current_match_date - pm_date).days
                # Ponderar solo partidos jugados en los últimos 730 días (2 años) para mayor relevancia
                if 0 <= days_ago <= 730:
                    pm_copy = pm.copy()
                    pm_copy["days_ago"] = float(days_ago)
                    training_data.append(pm_copy)
            
            dc_model = DixonColesModel()
            # Ajustar con 100 iteraciones para velocidad en el loop del backtest
            dc_model.fit(training_data, iterations=100, learning_rate=0.15)
            
        # Predicción probabilística
        pred = dc_model.predict_probabilities(home, away)
        prob_h = pred["home_win_probability"] / 100.0
        prob_d = pred["draw_probability"] / 100.0
        prob_a = pred["away_win_probability"] / 100.0
        
        # Obtener cuotas reales de Bet365
        odds_h = match.get("b365_home")
        odds_d = match.get("b365_draw")
        odds_a = match.get("b365_away")
        
        if not odds_h or not odds_d or not odds_a:
            continue
            
        # Calcular valor esperado (edges)
        edge_h = (prob_h * odds_h) - 1.0
        edge_d = (prob_d * odds_d) - 1.0
        edge_a = (prob_a * odds_a) - 1.0
        
        # Buscar el mayor valor esperado positivo
        best_bet = None
        best_edge = -1.0
        best_odds = 0.0
        result_key = ""
        
        if edge_h >= min_edge and edge_h > best_edge:
            best_bet = "H"
            best_edge = edge_h
            best_odds = odds_h
            result_key = "H"
        if edge_d >= min_edge and edge_d > best_edge:
            best_bet = "D"
            best_edge = edge_d
            best_odds = odds_d
            result_key = "D"
        if edge_a >= min_edge and edge_a > best_edge:
            best_bet = "A"
            best_edge = edge_a
            best_odds = odds_a
            result_key = "A"
            
        if best_bet and bankroll > 10.0:
            # Tamaño de apuesta utilizando el Criterio de Kelly Fraccionado
            # f* = (p * b - q) / b = (edge) / (odds - 1)
            raw_kelly = best_edge / (best_odds - 1.0)
            stake_pct = raw_kelly * kelly_fraction
            
            # Limitar la apuesta a un máximo de 2% de la banca por partido para mitigar riesgo de ruina
            if stake_pct > 0.02:
                stake_pct = 0.02
            elif stake_pct < 0.002:
                stake_pct = 0.002
                
            stake_amount = bankroll * stake_pct
            actual_result = match["result"]
            
            total_bets += 1
            total_staked += stake_amount
            
            # Evaluar resultado financiero
            won = (actual_result == best_bet)
            if won:
                bets_won += 1
                payout = stake_amount * best_odds
                profit = payout - stake_amount
                bankroll += profit
                total_returned += payout
            else:
                profit = -stake_amount
                bankroll += profit
                
            if bankroll > peak_bankroll:
                peak_bankroll = bankroll
                
            # Calcular drawdown actual
            dd = (peak_bankroll - bankroll) / peak_bankroll * 100.0
            if dd > max_drawdown:
                max_drawdown = dd
                
            bet_history.append({
                "date": match["date"],
                "match": f"{home} vs {away}",
                "bet": best_bet,
                "odds": best_odds,
                "edge": best_edge,
                "stake_usd": stake_amount,
                "result": actual_result,
                "profit_usd": profit,
                "bankroll_usd": bankroll
            })
            
    # Resultados consolidados
    net_profit = bankroll - initial_bankroll
    roi = (net_profit / initial_bankroll) * 100.0 if initial_bankroll > 0 else 0.0
    yield_pct = ((total_returned - total_staked) / total_staked * 100.0) if total_staked > 0 else 0.0
    win_rate = (bets_won / total_bets * 100.0) if total_bets > 0 else 0.0
    
    print(f"[Backtester] --- RESULTADOS FINALES: {division_filter or 'TODAS'} ---")
    print(f"  * Apuestas realizadas: {total_bets} | Ganadas: {bets_won} | Efectividad: {win_rate:.1f}%")
    print(f"  * Volumen total apostado: ${total_staked:.2f} USD | Retornado: ${total_returned:.2f} USD")
    print(f"  * Ganancia Neta: ${net_profit:.2f} USD | ROI: {roi:.1f}% | Yield Financiero: {yield_pct:.2f}%")
    print(f"  * drawdown Máximo: {max_drawdown:.1f}% | Banca Final: ${bankroll:.2f} USD")
    
    return {
        "division": division_filter or "TODAS",
        "apuestas_totales": total_bets,
        "apuestas_ganadas": bets_won,
        "efectividad_porcentaje": win_rate,
        "total_apostado": total_staked,
        "ganancia_neta": net_profit,
        "roi_porcentaje": roi,
        "yield_porcentaje": yield_pct,
        "drawdown_maximo_porcentaje": max_drawdown,
        "banca_final": bankroll,
        "historial_reciente": bet_history[-5:] # Últimas 5 apuestas realizadas
    }

def main():
    historical_data_path = "historical_results.json"
    
    if not os.path.exists(historical_data_path):
        print(f"[BacktestRunner] Error: No se encuentra {historical_data_path}. Ejecuta primero download_historical_data.py.")
        return
        
    with open(historical_data_path, "r", encoding="utf-8") as f:
        matches = json.load(f)
        
    # Correr backtest separado por liga
    laliga_results = run_backtest(matches, division_filter="SP1", initial_bankroll=1000.0)
    premier_results = run_backtest(matches, division_filter="E0", initial_bankroll=1000.0)
    
    # Escribir reporte estructurado del backtesting
    report_path = "backtest_summary.json"
    summary = {
        "fecha_ejecucion": datetime.now().isoformat(),
        "laliga": laliga_results,
        "premier": premier_results
    }
    
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
        
    print(f"\n[BacktestRunner] Resumen de pruebas retrospectivas guardado en: {report_path}")

if __name__ == "__main__":
    main()
