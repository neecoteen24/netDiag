from flask import Flask, jsonify, render_template, request

from main import run_diagnostics

app = Flask(__name__)


@app.after_request
def disable_cache(response):
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    return response


@app.get("/")
def index():
    return render_template("index.html")


@app.post("/api/diagnose")
def diagnose():
    payload = request.get_json(silent=True) or {}
    target = str(payload.get("target", "")).strip()

    if not target:
        return jsonify({"error": "Enter a domain, URL, or IP address."}), 400

    try:
        ports = [
            int(port) for port in str(payload.get("ports", "80,443")).split(",")
            if port.strip().isdigit()
        ]
        ports = ports or [80, 443]
        ports = sorted(set(port for port in ports if 1 <= port <= 65535))
        if not ports:
            return jsonify({"error": "Ports must be between 1 and 65535."}), 400

        report = run_diagnostics(
            target=target,
            ports=ports,
            include_udp=bool(payload.get("udp_probe")),
            include_trace=not bool(payload.get("no_trace")),
            scheme=str(payload.get("scheme", "https")).lower(),
        )
        return jsonify(report)
    except Exception as exc:
        app.logger.exception("Diagnostic run failed")
        return jsonify({"error": f"Diagnostic run failed: {exc}"}), 500


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
