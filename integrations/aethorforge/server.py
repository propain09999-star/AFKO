from pathlib import Path

from .telemetry import TelemetryEngine


def create_app():
    try:
        from flask import Flask, jsonify, request, send_from_directory
    except ImportError as exc:
        raise RuntimeError(
            "AETHORFORGE service requires Flask. Install integrations/aethorforge/requirements.txt."
        ) from exc

    app = Flask(__name__)
    telemetry = TelemetryEngine()
    ui_path = Path(__file__).with_name("ui")

    @app.route("/")
    def home():
        return send_from_directory(ui_path, "index.html")

    @app.route("/api/telemetry")
    def api_telemetry():
        return jsonify(telemetry.generate())

    @app.route("/api/query", methods=["POST"])
    def api_query():
        payload = request.get_json(silent=True) or {}
        query = payload.get("query", "")
        if not isinstance(query, str):
            return jsonify({"ok": False, "error": "query must be a string"}), 400
        telemetry.update_query(query[:4000])
        return jsonify({"ok": True, "query": telemetry.last_query})

    @app.route("/api/status", methods=["POST"])
    def api_status():
        payload = request.get_json(silent=True) or {}
        if not isinstance(payload, dict) or not isinstance(payload.get("state"), str):
            return jsonify({"ok": False, "error": "status requires a state"}), 400
        telemetry.update_afko_status(payload)
        return jsonify({"ok": True, "status": payload})

    @app.route("/api/history")
    def api_history():
        return jsonify({"history": telemetry.get_history()})

    return app


def run_server(host="127.0.0.1", port=8080):
    app = create_app()
    print(f"AETHORFORGE service listening at http://{host}:{port}")
    app.run(host=host, port=port, debug=False)