import math
from dixon_coles import DixonColesModel

def test_dixon_coles_basic():
    print("[TestDixonColes] Iniciando prueba unitaria básica...")
    
    # Conjunto mínimo de partidos sintéticos:
    # TeamA es un equipo fuerte que siempre gana goleando.
    # TeamB es un equipo débil que siempre pierde encajando muchos goles.
    # TeamC es un equipo intermedio.
    matches = [
        {"home": "TeamA", "away": "TeamB", "home_goals": 4, "away_goals": 0, "days_ago": 1.0},
        {"home": "TeamB", "away": "TeamA", "home_goals": 0, "away_goals": 3, "days_ago": 2.0},
        {"home": "TeamA", "away": "TeamC", "home_goals": 2, "away_goals": 0, "days_ago": 3.0},
        {"home": "TeamC", "away": "TeamA", "home_goals": 0, "away_goals": 1, "days_ago": 4.0},
        {"home": "TeamC", "away": "TeamB", "home_goals": 2, "away_goals": 1, "days_ago": 5.0},
        {"home": "TeamB", "away": "TeamC", "home_goals": 1, "away_goals": 2, "days_ago": 6.0},
    ]
    
    model = DixonColesModel()
    # Calibrar el modelo
    model.fit(matches, learning_rate=0.01, iterations=150)
    
    norm_a = model.normalize_team("TeamA")
    norm_b = model.normalize_team("TeamB")
    norm_c = model.normalize_team("TeamC")

    # Imprimir parámetros para inspección
    print(f" - Ataque TeamA: {model.attacks[norm_a]:.3f} | Defensa: {model.defenses[norm_a]:.3f}")
    print(f" - Ataque TeamB: {model.attacks[norm_b]:.3f} | Defensa: {model.defenses[norm_b]:.3f}")
    print(f" - Ataque TeamC: {model.attacks[norm_c]:.3f} | Defensa: {model.defenses[norm_c]:.3f}")
    
    # Aseverar lógica básica: el ataque de TeamA debe ser mayor que el de TeamB
    assert model.attacks[norm_a] > model.attacks[norm_b], "El ataque de TeamA debería ser mayor que el de TeamB"
    # La defensa de TeamA debe ser mejor (valor más bajo de debilidad defensiva) que TeamB
    assert model.defenses[norm_a] < model.defenses[norm_b], "La defensa de TeamA (debilidad) debería ser mejor (número más bajo) que TeamB"
    
    # Probar predicción
    pred = model.predict_probabilities("TeamA", "TeamB")
    print(f" - Predicción TeamA vs TeamB:")
    print(f"   * Victoria Local (TeamA): {pred['home_win_probability']:.2f}%")
    print(f"   * Empate: {pred['draw_probability']:.2f}%")
    print(f"   * Victoria Visitante (TeamB): {pred['away_win_probability']:.2f}%")
    
    # Aseverar que las probabilidades suman 100% aproximadamente (tolerancia de coma flotante)
    total_prob = pred['home_win_probability'] + pred['draw_probability'] + pred['away_win_probability']
    assert abs(total_prob - 100.0) < 1e-2, f"Las probabilidades suman {total_prob}%, deberían sumar 100%"
    
    print("[TestDixonColes] ¡ÉXITO! Las aseveraciones matemáticas y lógicas pasaron.")
    return True

if __name__ == "__main__":
    try:
        test_dixon_coles_basic()
    except AssertionError as e:
        print(f"[TestDixonColes] FALLO de aseveración: {e}")
        import sys
        sys.exit(1)
    except Exception as e:
        print(f"[TestDixonColes] ERROR inesperado: {e}")
        import sys
        sys.exit(1)
