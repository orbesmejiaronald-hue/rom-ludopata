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

    if not local or not visitor:
        return Response(
            "data: " + json.dumps({"status": "error", "message": "Equipos no provistos."}) + "\n\n",
            mimetype="text/event-stream"
        )

    def generate():
        try:
            generator = _coordinator.run_full_analysis_generator(local, visitor)
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
