import math
import unicodedata
import re

def calculate_tau(x: int, y: int, lmbda: float, mu: float, rho: float) -> float:
    """
    Factor de corrección de Dixon-Coles para marcadores con baja anotación.
    Garantiza que el valor de retorno sea estrictamente positivo.
    """
    if x == 0 and y == 0:
        val = 1.0 - lmbda * mu * rho
    elif x == 1 and y == 0:
        val = 1.0 + mu * rho
    elif x == 0 and y == 1:
        val = 1.0 + lmbda * rho
    elif x == 1 and y == 1:
        val = 1.0 - rho
    else:
        val = 1.0
    return max(1e-8, val)

def d_ln_tau_d_lambda(x: int, y: int, lmbda: float, mu: float, rho: float) -> float:
    tau = calculate_tau(x, y, lmbda, mu, rho)
    if tau < 1e-6:
        tau = 1e-6
    if x == 0 and y == 0:
        return -mu * rho / tau
    elif x == 0 and y == 1:
        return rho / tau
    else:
        return 0.0

def d_ln_tau_d_mu(x: int, y: int, lmbda: float, mu: float, rho: float) -> float:
    tau = calculate_tau(x, y, lmbda, mu, rho)
    if tau < 1e-6:
        tau = 1e-6
    if x == 0 and y == 0:
        return -lmbda * rho / tau
    elif x == 1 and y == 0:
        return rho / tau
    else:
        return 0.0

def d_ln_tau_d_rho(x: int, y: int, lmbda: float, mu: float, rho: float) -> float:
    tau = calculate_tau(x, y, lmbda, mu, rho)
    if tau < 1e-6:
        tau = 1e-6
    if x == 0 and y == 0:
        return -lmbda * mu / tau
    elif x == 1 and y == 0:
        return mu / tau
    elif x == 0 and y == 1:
        return lmbda / tau
    elif x == 1 and y == 1:
        return -1.0 / tau
    else:
        return 0.0

def log_poisson(k: int, lmbda: float) -> float:
    if lmbda <= 0:
        return -100.0
    return -lmbda + k * math.log(lmbda) - math.lgamma(k + 1)

class DixonColesModel:
    def __init__(self):
        self.attacks = {}
        self.defenses = {}
        self.home_advantage = 1.15
        self.rho = 0.0
        self.teams = []

    def normalize_team(self, name: str) -> str:
        """
        Normaliza el nombre de un equipo para evitar desajustes por mayúsculas, acentos, 
        sufijos comunes (FC, CF, Club, etc.) y aliases de ligas.
        """
        if not name:
            return ""
        # Convertir a minúsculas y quitar espacios en extremos
        s = name.lower().strip()
        # Eliminar acentos
        s = ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')
        # Eliminar puntuaciones
        s = re.sub(r'[^\w\s]', '', s)
        # Eliminar palabras sueltas irrelevantes al inicio o al final
        s = re.sub(r'\b(fc|cf|club|cd|ud|sd|de|the)\b', '', s)
        # Quitar espacios extra
        s = re.sub(r'\s+', ' ', s).strip()
        
        # Diccionario de aliases y mapeos comunes
        mappings = {
            "manchester united": "man united",
            "manchester city": "man city",
            "man utd": "man united",
            "man city": "man city",
            "athletic club": "athletic bilbao",
            "athletic": "athletic bilbao",
            "bilbao": "athletic bilbao",
            "atletico": "atletico madrid",
            "atletico de madrid": "atletico madrid",
            "celta": "celta vigo",
            "real betis": "betis",
            "depor": "deportivo",
            "real madrid": "real madrid",
            "real sociedad": "real sociedad",
            "sociedad": "real sociedad",
            "rayo": "rayo vallecano",
            "vallecano": "rayo vallecano",
            "sheffield utd": "sheffield united",
            "sheffield": "sheffield united",
            "tottenham hotspur": "tottenham",
            "spurs": "tottenham",
            "west ham united": "west ham",
            "wolverhampton": "wolves",
            "wolverhampton wanderers": "wolves",
        }
        
        if s in mappings:
            return mappings[s]
            
        for key, val in mappings.items():
            if key in s:
                return val
                
        return s

    def fit(self, matches: list, learning_rate: float = 0.15, iterations: int = 150, phi: float = 0.0019):
        """
        Calibra el modelo Dixon-Coles utilizando ascenso de gradiente normalizado en Python puro.
        matches: lista de dicts con claves {'home': str, 'away': str, 'home_goals': int, 'away_goals': int, 'days_ago': float}
        """
        # Normalizar nombres de equipos en los partidos de entrenamiento
        normalized_matches = []
        teams_set = set()
        for m in matches:
            m_norm = m.copy()
            m_norm['home'] = self.normalize_team(m['home'])
            m_norm['away'] = self.normalize_team(m['away'])
            normalized_matches.append(m_norm)
            teams_set.add(m_norm['home'])
            teams_set.add(m_norm['away'])
            
        self.teams = sorted(list(teams_set))
        
        if not self.teams:
            return
            
        # Inicializar parámetros
        self.attacks = {t: 1.0 for t in self.teams}
        self.defenses = {t: 1.0 for t in self.teams}
        self.home_advantage = 1.15
        self.rho = 0.0
        
        # Precomputar pesos y sumas de pesos por equipo y total
        weights = []
        total_weight = 0.0
        total_weight_team = {t: 0.0 for t in self.teams}
        
        for m in normalized_matches:
            t_k = m.get('days_ago', 0.0)
            w = math.exp(-phi * t_k)
            weights.append(w)
            total_weight += w
            
            h = m['home']
            a = m['away']
            total_weight_team[h] += w
            total_weight_team[a] += w
            
        # Evitar divisiones por cero
        if total_weight == 0.0:
            total_weight = 1.0
        for t in self.teams:
            if total_weight_team[t] == 0.0:
                total_weight_team[t] = 1.0
                
        print(f"[DixonColes] Calibrando modelo con {len(matches)} partidos para {len(self.teams)} equipos (Gradientes Normalizados)...")
        
        for iteration in range(iterations):
            # Calcular lambdas y mus actuales
            lambdas = []
            mus = []
            for m in normalized_matches:
                h = m['home']
                a = m['away']
                lambdas.append(self.attacks[h] * self.defenses[a] * self.home_advantage)
                mus.append(self.attacks[a] * self.defenses[h])
                
            grad_attack = {t: 0.0 for t in self.teams}
            grad_defense = {t: 0.0 for t in self.teams}
            grad_home_adv = 0.0
            grad_rho = 0.0
            
            for idx, m in enumerate(normalized_matches):
                h = m['home']
                a = m['away']
                x = m['home_goals']
                y = m['away_goals']
                w = weights[idx]
                
                l = lambdas[idx]
                mu = mus[idx]
                
                # Clip para estabilidad numérica
                if l < 1e-4: l = 1e-4
                if mu < 1e-4: mu = 1e-4
                
                # Derivadas de log-verosimilitud
                d_ln_tau_dl = d_ln_tau_d_lambda(x, y, l, mu, self.rho)
                d_ln_tau_dmu = d_ln_tau_d_mu(x, y, l, mu, self.rho)
                
                d_ll_dl = d_ln_tau_dl - 1.0 + (x / l)
                d_ll_dmu = d_ln_tau_dmu - 1.0 + (y / mu)
                
                # Acumular gradientes ponderados
                grad_attack[h] += w * d_ll_dl * self.defenses[a] * self.home_advantage
                grad_attack[a] += w * d_ll_dmu * self.defenses[h]
                
                grad_defense[a] += w * d_ll_dl * self.attacks[h] * self.home_advantage
                grad_defense[h] += w * d_ll_dmu * self.attacks[a]
                
                grad_home_adv += w * d_ll_dl * self.attacks[h] * self.defenses[a]
                grad_rho += w * d_ln_tau_d_rho(x, y, l, mu, self.rho)
                
            # Actualizar parámetros usando gradiente promedio normalizado
            for t in self.teams:
                self.attacks[t] += learning_rate * (grad_attack[t] / total_weight_team[t])
                self.defenses[t] += learning_rate * (grad_defense[t] / total_weight_team[t])
                
                # Clip de prevención de negativos
                if self.attacks[t] < 0.05: self.attacks[t] = 0.05
                if self.defenses[t] < 0.05: self.defenses[t] = 0.05
                
            self.home_advantage += learning_rate * (grad_home_adv / total_weight)
            if self.home_advantage < 0.5: self.home_advantage = 0.5
            
            self.rho += learning_rate * (grad_rho / total_weight)
            if self.rho < -0.3: self.rho = -0.3
            if self.rho > 0.3: self.rho = 0.3
            
            # Restricción de normalización: media de ataques = 1.0 y de defensas = 1.0
            mean_attack = sum(self.attacks[t] for t in self.teams) / len(self.teams)
            mean_defense = sum(self.defenses[t] for t in self.teams) / len(self.teams)
            for t in self.teams:
                self.attacks[t] /= mean_attack
                self.defenses[t] /= mean_defense
                
        print(f"[DixonColes] Calibración terminada. Parámetro de Empates (Rho) = {self.rho:.4f} | Ventaja de Local = {self.home_advantage:.3f}")

    def predict_probabilities(self, home: str, away: str, neutral_venue: bool = False) -> dict:
        """
        Retorna las probabilidades exactas del partido de fútbol aplicando la normalización de nombres.
        """
        home_norm = self.normalize_team(home)
        away_norm = self.normalize_team(away)
        
        alpha_h = self.attacks.get(home_norm, 1.0)
        beta_a = self.defenses.get(away_norm, 1.0)
        alpha_a = self.attacks.get(away_norm, 1.0)
        beta_h = self.defenses.get(home_norm, 1.0)
        
        h_adv = 1.0 if neutral_venue else self.home_advantage
        lmbda = alpha_h * beta_a * h_adv
        mu = alpha_a * beta_h
        
        max_goals = 8
        prob_matrix = [[0.0 for _ in range(max_goals)] for _ in range(max_goals)]
        
        def poisson_pmf(k, lmb):
            # Evitar desbordamiento o lambdas <= 0
            if lmb <= 0:
                return 1.0 if k == 0 else 0.0
            return (math.exp(-lmb) * (lmb**k)) / math.factorial(k)
            
        for x in range(max_goals):
            for y in range(max_goals):
                p_x = poisson_pmf(x, lmbda)
                p_y = poisson_pmf(y, mu)
                tau = calculate_tau(x, y, lmbda, mu, self.rho)
                prob_matrix[x][y] = tau * p_x * p_y
                
        # Normalizar matriz
        total_p = sum(sum(row) for row in prob_matrix)
        if total_p > 0:
            for x in range(max_goals):
                for y in range(max_goals):
                    prob_matrix[x][y] /= total_p
                    
        home_win = 0.0
        draw = 0.0
        away_win = 0.0
        
        for x in range(max_goals):
            for y in range(max_goals):
                if x > y:
                    home_win += prob_matrix[x][y]
                elif x == y:
                    draw += prob_matrix[x][y]
                else:
                    away_win += prob_matrix[x][y]
                    
        return {
            "home_lambda": lmbda,
            "away_lambda": mu,
            "home_win_probability": home_win * 100,
            "draw_probability": draw * 100,
            "away_win_probability": away_win * 100,
            "matrix": prob_matrix
        }
