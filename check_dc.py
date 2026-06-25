import json
import math
from dixon_coles import DixonColesModel

def calculate_log_likelihood(model, matches):
    ll = 0.0
    for m in matches:
        h = model.normalize_team(m['home'])
        a = model.normalize_team(m['away'])
        x = m['home_goals']
        y = m['away_goals']
        
        # Check if teams are in the fitted model
        alpha_h = model.attacks.get(h, 1.0)
        beta_a = model.defenses.get(a, 1.0)
        alpha_a = model.attacks.get(a, 1.0)
        beta_h = model.defenses.get(h, 1.0)
        
        lmbda = alpha_h * beta_a * model.home_advantage
        mu = alpha_a * beta_h
        
        if lmbda < 1e-4: lmbda = 1e-4
        if mu < 1e-4: mu = 1e-4
        
        # Dixon-Coles adjustment
        tau = 1.0
        if x == 0 and y == 0:
            tau = 1.0 - lmbda * mu * model.rho
        elif x == 1 and y == 0:
            tau = 1.0 + mu * model.rho
        elif x == 0 and y == 1:
            tau = 1.0 + lmbda * model.rho
        elif x == 1 and y == 1:
            tau = 1.0 - model.rho
            
        tau = max(1e-8, tau)
        
        # Log-Poisson for home goals
        ll_h = -lmbda + x * math.log(lmbda) - math.lgamma(x + 1)
        # Log-Poisson for away goals
        ll_a = -mu + y * math.log(mu) - math.lgamma(y + 1)
        
        ll += math.log(tau) + ll_h + ll_a
    return ll

def test():
    with open("historical_results.json", "r", encoding="utf-8") as f:
        matches = json.load(f)
        
    # Filter SP1
    sp1_matches = [m for m in matches if m["div"] == "SP1"]
    
    print(f"Total SP1 matches: {len(sp1_matches)}")
    
    # Try different learning rates
    for lr in [0.01, 0.05, 0.1, 0.15, 0.2, 0.3]:
        model = DixonColesModel()
        print(f"\n--- Testing LR = {lr} ---")
        # Let's intercept the fit to print likelihood every 10 iterations
        # We will run fit manually or copy the logic to print likelihood
        model.fit(sp1_matches, learning_rate=lr, iterations=100)
        final_ll = calculate_log_likelihood(model, sp1_matches)
        print(f"Final log-likelihood: {final_ll:.4f}")
        print(f"Home Adv: {model.home_advantage:.4f} | Rho: {model.rho:.4f}")

if __name__ == "__main__":
    test()
