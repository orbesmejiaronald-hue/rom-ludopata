import os
import re
import json
import unicodedata
import requests

LEAGUES = {
    "ita.1": {"name": "Serie A (Italia)", "country": "Italy", "flag": "🇮🇹"},
    "eng.1": {"name": "Premier League (Inglaterra)", "country": "England", "flag": "🏴󠁧󠁢󠁥󠁮󠁧󠁿"},
    "esp.1": {"name": "LaLiga (España)", "country": "Spain", "flag": "🇪🇸"},
    "uefa.champions": {"name": "UEFA Champions League", "country": "Europe", "flag": "🏆"},
    "ger.1": {"name": "Bundesliga (Alemania)", "country": "Germany", "flag": "🇩🇪"},
    "fra.1": {"name": "Ligue 1 (Francia)", "country": "France", "flag": "🇫🇷"},
    "eng.2": {"name": "Championship (Inglaterra)", "country": "England", "flag": "🏴󠁧󠁢󠁥󠁮󠁧󠁿"},
    "ned.1": {"name": "Eredivisie (Países Bajos)", "country": "Netherlands", "flag": "🇳🇱"},
    "por.1": {"name": "Primeira Liga (Portugal)", "country": "Portugal", "flag": "🇵🇹"},
    "ksa.1": {"name": "Saudi Pro League (Arabia)", "country": "Saudi Arabia", "flag": "🇸🇦"},
    "usa.1": {"name": "MLS (Estados Unidos)", "country": "USA", "flag": "🇺🇸"},
    "mex.1": {"name": "Liga MX (México)", "country": "Mexico", "flag": "🇲🇽"},
    "bra.1": {"name": "Brasileirão (Brasil)", "country": "Brazil", "flag": "🇧🇷"},
    "arg.1": {"name": "Liga Profesional (Argentina)", "country": "Argentina", "flag": "🇦🇷"},
    "uefa.europa": {"name": "UEFA Europa League", "country": "Europe", "flag": "🇪🇺"},
    "conmebol.libertadores": {"name": "Copa Libertadores", "country": "South America", "flag": "🌎"}
}

class LiveDataProvider:
    def __init__(self, timeout: int = 5):
        self.timeout = timeout
        self.headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        self.base_url = "https://site.api.espn.com/apis/site/v2/sports/soccer"

    def normalize_name(self, name: str) -> str:
        if not name:
            return ""
        s = name.lower().strip()
        s = ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')
        s = re.sub(r'[^\w\s]', '', s)
        s = re.sub(r'\b(fc|cf|club|cd|ud|sd|de|the|as|ac|ss)\b', '', s)
        return re.sub(r'\s+', ' ', s).strip()

    def get_today_matches(self, league_code: str = "ita.1") -> list:
        """
        Obtiene los partidos programados o jugados de la jornada actual para la liga especificada.
        """
        url = f"{self.base_url}/{league_code}/scoreboard"
        try:
            r = requests.get(url, headers=self.headers, timeout=self.timeout)
            if r.status_code != 200:
                print(f"[LiveDataProvider] Error status {r.status_code} al consultar {league_code}")
                return []
            
            data = r.json()
            events = data.get("events", [])
            matches = []

            for ev in events:
                ev_id = ev.get("id")
                status_info = ev.get("status", {}).get("type", {})
                status_state = status_info.get("state", "pre") # pre, in, post
                status_desc = status_info.get("description", "Scheduled")
                status_detail = status_info.get("detail", status_desc)
                
                competitors = ev.get("competitions", [{}])[0].get("competitors", [])
                home_team = {}
                away_team = {}
                for comp in competitors:
                    if comp.get("homeAway") == "home":
                        home_team = comp
                    else:
                        away_team = comp

                home_name = home_team.get("team", {}).get("displayName", "Local")
                away_name = away_team.get("team", {}).get("displayName", "Visitante")
                home_score = home_team.get("score")
                away_score = away_team.get("score")

                matches.append({
                    "id": ev_id,
                    "league_code": league_code,
                    "league_name": LEAGUES.get(league_code, {}).get("name", league_code),
                    "home_team": home_name,
                    "away_team": away_name,
                    "home_score": home_score,
                    "away_score": away_score,
                    "utc_date": ev.get("date"),
                    "status_state": status_state,
                    "status_desc": status_desc,
                    "status_detail": status_detail,
                    "has_lineups": False
                })

            return matches
        except Exception as e:
            print(f"[LiveDataProvider] Error consultando partidos de {league_code}: {e}")
            return []

    def get_match_summary(self, event_id: str, league_code: str = "ita.1") -> dict:
        """
        Obtiene alineaciones oficiales (titulares y suplentes), estadio, árbitro y cuotas reales de mercado.
        """
        url = f"{self.base_url}/{league_code}/summary?event={event_id}"
        try:
            r = requests.get(url, headers=self.headers, timeout=self.timeout)
            if r.status_code != 200:
                return {}
            
            data = r.json()
            result = {
                "event_id": event_id,
                "league_code": league_code,
                "home_lineup": [],
                "away_lineup": [],
                "home_subs": [],
                "away_subs": [],
                "has_official_lineups": False,
                "stadium": "No especificado",
                "referee": "No especificado",
                "odds": None
            }

            # 1. Alineaciones de rosters
            rosters = data.get("rosters", [])
            for r_team in rosters:
                is_home = (r_team.get("homeAway") == "home")
                roster_entries = r_team.get("roster", [])
                
                starters = []
                bench = []
                for entry in roster_entries:
                    athlete = entry.get("athlete", {})
                    p_name = athlete.get("displayName", "")
                    pos = entry.get("position", {}).get("abbreviation", "SUB")
                    starter_flag = entry.get("starter", False)
                    jersey = entry.get("jersey", "")

                    p_info = {
                        "name": p_name,
                        "position": pos,
                        "jersey": jersey
                    }

                    if starter_flag:
                        starters.append(p_info)
                    else:
                        bench.append(p_info)

                if is_home:
                    result["home_lineup"] = starters
                    result["home_subs"] = bench
                else:
                    result["away_lineup"] = starters
                    result["away_subs"] = bench

            if len(result["home_lineup"]) >= 11 and len(result["away_lineup"]) >= 11:
                result["has_official_lineups"] = True

            # 2. Estadio y árbitro
            game_info = data.get("gameInfo", {})
            venue = game_info.get("venue", {})
            if venue:
                result["stadium"] = f"{venue.get('fullName', '')} ({venue.get('address', {}).get('city', '')})"
            
            officials = game_info.get("officials", [])
            if officials:
                result["referee"] = officials[0].get("displayName", "Desconocido")

            # 2.5 Historial de forma reciente (Últimos 5 partidos de cada equipo)
            last_5 = data.get("lastFiveGames", [])
            home_recent = []
            away_recent = []
            for team_l5 in last_5:
                t_is_home = (team_l5.get("homeAway") == "home" or result.get("home_team_name", "").lower() in team_l5.get("team", {}).get("displayName", "").lower())
                events_l5 = team_l5.get("events", [])
                for e in events_l5[:5]:
                    entry = {
                        "opponent": e.get("opponent", {}).get("displayName", ""),
                        "result": e.get("gameResult", "D"), # W, D, L
                        "score": e.get("score", "-")
                    }
                    if t_is_home:
                        home_recent.append(entry)
                    else:
                        away_recent.append(entry)

            result["home_last_5"] = home_recent
            result["away_last_5"] = away_recent

            # 3. Cuotas de mercado vivas (DraftKings u otro proveedor)
            odds_list = data.get("odds", [])
            if odds_list:
                o0 = odds_list[0]
                result["odds"] = {
                    "provider": o0.get("provider", {}).get("name", "DraftKings"),
                    "details": o0.get("details", ""),
                    "over_under": o0.get("overUnder"),
                    "home_moneyline": o0.get("homeTeamOdds", {}).get("moneyLine"),
                    "away_moneyline": o0.get("awayTeamOdds", {}).get("moneyLine")
                }

            return result
        except Exception as e:
            print(f"[LiveDataProvider] Error obteniendo resumen para evento {event_id}: {e}")
            return {}

    def find_match_by_teams(self, local_team: str, visitor_team: str) -> dict:
        """
        Busca si el partido especificado está programado o en vivo en las ligas soportadas.
        """
        loc_norm = self.normalize_name(local_team)
        vis_norm = self.normalize_name(visitor_team)

        for l_code in LEAGUES.keys():
            matches = self.get_today_matches(l_code)
            for m in matches:
                h_norm = self.normalize_name(m["home_team"])
                a_norm = self.normalize_name(m["away_team"])

                if (loc_norm in h_norm or h_norm in loc_norm) and (vis_norm in a_norm or a_norm in vis_norm):
                    print(f"[LiveDataProvider] ¡Coincidencia en vivo encontrada en {l_code}: {m['home_team']} vs {m['away_team']} (ID: {m['id']})!")
                    summary = self.get_match_summary(m["id"], l_code)
                    m.update(summary)
                    return m

        return {}

    def get_featured_matches(self, limit: int = 6) -> list:
        """
        Obtiene los partidos más destacados del día entre todas las ligas activas.
        Prioriza partidos en vivo > programados hoy con alineaciones > ligas principales.
        """
        priority_leagues = [
            "ita.1", "eng.1", "esp.1", "uefa.champions", "ger.1", "fra.1",
            "eng.2", "ned.1", "por.1", "ksa.1", "usa.1", "mex.1", "bra.1"
        ]
        all_candidates = []

        for l_code in priority_leagues:
            matches = self.get_today_matches(l_code)
            for m in matches:
                # Priorizar en vivo (prio 1) > programados hoy (prio 2) > finalizados hoy (prio 3)
                prio = 3
                if m.get("status_state") == "in":
                    prio = 1
                elif m.get("status_state") == "pre":
                    prio = 2
                all_candidates.append((prio, m))

        all_candidates.sort(key=lambda x: x[0])
        featured = [item[1] for item in all_candidates[:limit]]
        return featured

if __name__ == "__main__":
    provider = LiveDataProvider()
    matches = provider.get_today_matches("ita.1")
    print(f"Partidos Serie A hoy ({len(matches)}):")
    for m in matches:
        print(f" - {m['home_team']} vs {m['away_team']} | Estado: {m['status_detail']}")
