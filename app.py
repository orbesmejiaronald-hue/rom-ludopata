import json
import os
from flask import Flask, Response, request, send_from_directory, render_template

app = Flask(__name__, static_folder="static", template_folder="templates")

# Crear carpetas estáticas y de plantillas si no existen
os.makedirs(os.path.join(app.root_path, "templates"), exist_ok=True)
os.makedirs(os.path.join(app.root_path, "static"), exist_ok=True)

# ── MEJORA C: Singleton del coordinator ──────────────────────────────────────
# Se instancia una sola vez al arrancar el servidor, no en cada request.
from agent_coordinator import AgentCoordinator
_coordinator = AgentCoordinator()
# ─────────────────────────────────────────────────────────────────────────────

# ── MEJORA D: Cabeceras CORS globales ────────────────────────────────────────
@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return response
# ─────────────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/service-worker.js")
def service_worker():
    return send_from_directory(app.static_folder, "service-worker.js")

@app.route("/manifest.json")
def manifest():
    return send_from_directory(app.static_folder, "manifest.json")

@app.route("/api/analyze")
def analyze():
    local = request.args.get("local", "").strip()
    visitor = request.args.get("visitor", "").strip()
    neutral = request.args.get("neutral", "false").strip().lower() == "true"

    if not local or not visitor:
        return Response(
            "data: " + json.dumps({"status": "error", "message": "Equipos no provistos."}) + "\n\n",
            mimetype="text/event-stream"
        )

    def generate():
        try:
            generator = _coordinator.run_full_analysis_generator(local, visitor, neutral_venue_override=neutral)
            for event in generator:
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        except Exception as e:
            import traceback
            traceback.print_exc()
            yield f"data: {json.dumps({'status': 'error', 'message': f'Error en el análisis: {str(e)}'}, ensure_ascii=False)}\n\n"

    response = Response(generate(), mimetype="text/event-stream")
    response.headers["Cache-Control"] = "no-cache"
    response.headers["X-Accel-Buffering"] = "no"
    return response

@app.route("/api/chat")
def chat():
    # Soporta GET con params para EventSource
    message = request.args.get("message", "").strip()
    
    if not message:
        # Intentar POST fallback por si acaso
        if request.method == "POST":
            try:
                data = request.get_json() or {}
                message = data.get("message", "").strip()
            except:
                pass
                
    if not message:
        return Response(
            "data: " + json.dumps({"status": "error", "message": "Mensaje vacío."}) + "\n\n",
            mimetype="text/event-stream"
        )

    def generate_chat():
        try:
            # 1. Decidir si requiere búsqueda en internet
            search_prompt = f"""
            Analiza el mensaje del usuario para un chat de apuestas y pronósticos deportivos:
            "{message}"
            
            Determina si responder a este mensaje requiere buscar información actualizada en tiempo real en internet (como alineaciones, resultados recientes, cuotas, árbitros, etc.).
            - Si requiere búsqueda, responde ÚNICAMENTE con los términos de búsqueda óptimos en inglés o español (máximo 5-6 palabras).
            - Si no requiere búsqueda (ej. saludos, preguntas generales sobre apuestas, explicaciones de conceptos o sobre el funcionamiento de la app), responde con la palabra 'NO_SEARCH'.
            
            Respuesta:
            """
            
            search_query = _coordinator.gemini_client.generate_content(search_prompt).strip()
            
            context = ""
            search_results = []
            if "NO_SEARCH" not in search_query and len(search_query) > 2:
                yield f"data: {json.dumps({'status': 'searching', 'message': f'Buscando en internet: {search_query}...'}, ensure_ascii=False)}\n\n"
                search_results = _coordinator.collector.search_duckduckgo(search_query, max_results=5)
                if search_results:
                    context = "Información obtenida de internet en tiempo real:\n"
                    for res in search_results:
                        context += f"- Enlace: {res['url']}\n  Contenido: {res['snippet']}\n"
                    yield f"data: {json.dumps({'status': 'context_found', 'message': 'Analizando información recopilada...'}, ensure_ascii=False)}\n\n"
                else:
                    yield f"data: {json.dumps({'status': 'no_results', 'message': 'No se encontraron resultados en internet, respondiendo con conocimiento interno...'}, ensure_ascii=False)}\n\n"
            
            system_instruction = """
            Eres SBIE (Sports Betting Intelligence Engine v2.0) integrado en el chat de ROM LUDOPATA 1.2.
            No eres un tipster ni haces apuestas impulsivas. Tu objetivo es realizar un análisis probabilístico objetivo sustentado únicamente en evidencia disponible.
            Si te proveen contexto de internet en tiempo real, úsalo rigurosamente. Si la información es insuficiente o no existe, admítelo.
            Nunca inventes estadísticas, lesiones o cuotas. Mantén un tono de analista financiero de apuestas premium (+EV, Kelly, gestión de riesgo). Prohibido usar palabras como 'apuesta segura' o 'ganador garantizado'. Responde en español en Markdown limpio.
            """
            
            prompt = f"""
            Mensaje del usuario: {message}
            
            {context}
            
            Responde al usuario en español usando formato Markdown limpio.
            """
            
            yield f"data: {json.dumps({'status': 'generating'}, ensure_ascii=False)}\n\n"
            
            stream_gen = _coordinator.gemini_client.generate_content_stream(prompt, system_instruction=system_instruction)
            for chunk in stream_gen:
                yield f"data: {json.dumps({'status': 'chunk', 'text': chunk}, ensure_ascii=False)}\n\n"
            
            yield f"data: {json.dumps({'status': 'done'}, ensure_ascii=False)}\n\n"
            
        except Exception as e:
            yield f"data: {json.dumps({'status': 'error', 'message': f'Error en el chat: {str(e)}'}, ensure_ascii=False)}\n\n"

    response = Response(generate_chat(), mimetype="text/event-stream")
    response.headers["Cache-Control"] = "no-cache"
    response.headers["X-Accel-Buffering"] = "no"
    return response

@app.route("/api/backtest")
def backtest():
    try:
        with open("backtest_summary.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        return Response(json.dumps(data, ensure_ascii=False), mimetype="application/json")
    except Exception as e:
        return Response(json.dumps({"error": str(e)}), status=500, mimetype="application/json")

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
