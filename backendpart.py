import json
import os
import random
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HOST = "127.0.0.1"
PORT = 5050
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HTML_FILE = os.path.join(BASE_DIR, "index.html")
SCORE_FILE = os.path.join(BASE_DIR, "score.json")
ICON_FILE = os.path.join(BASE_DIR, "ITSROCK.png")

WEAPONS = {
    "rock": {"label": "Rock", "icon": "#icon-rock", "beats": "scissors"},
    "paper": {"label": "Paper", "icon": "#icon-paper", "beats": "rock"},
    "scissors": {"label": "Scissors", "icon": "#icon-scissors", "beats": "paper"},
}

DEFAULT_SCORE = {"player": 0, "draws": 0, "cpu": 0}


def read_score():
    if not os.path.exists(SCORE_FILE):
        write_score(DEFAULT_SCORE.copy())
        return DEFAULT_SCORE.copy()
    try:
        with open(SCORE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            raise ValueError("Invalid score format")
        return {
            "player": max(0, int(data.get("player", 0))),
            "draws": max(0, int(data.get("draws", 0))),
            "cpu": max(0, int(data.get("cpu", 0))),
        }
    except (OSError, ValueError, TypeError):
        fresh = DEFAULT_SCORE.copy()
        write_score(fresh)
        return fresh


def write_score(score_data):
    with open(SCORE_FILE, "w", encoding="utf-8") as f:
        json.dump(score_data, f, indent=2)


def evaluate_round(player_choice, cpu_choice):
    p_label = WEAPONS[player_choice]["label"].upper()
    c_label = WEAPONS[cpu_choice]["label"].upper()
    if player_choice == cpu_choice:
        return "draw", f"STALEMATE // BOTH DEPLOYED {p_label}"
    if WEAPONS[player_choice]["beats"] == cpu_choice:
        return "win", f"VICTORY // {p_label} OVERRIDES {c_label}"
    return "lose", f"BREACH // A.I. {c_label} DEFEATS {p_label}"


def load_html_page():
    with open(HTML_FILE, "r", encoding="utf-8") as f:
        return f.read()


class GameRequestHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def _write_bytes(self, body):
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            pass

    def send_json(self, payload, status_code=200):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self._write_bytes(body)

    def send_html(self, html_text, status_code=200):
        body = html_text.encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self._write_bytes(body)

    def read_json_body(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
        except ValueError:
            length = 0
        if length <= 0:
            return {}
        raw = self.rfile.read(length).decode("utf-8")
        return json.loads(raw)

    def do_GET(self):
        clean_path = self.path.split("?", 1)[0]
        if clean_path in ("/", "/index.html"):
            if os.path.exists(HTML_FILE):
                self.send_html(load_html_page(), 200)
            else:
                self.send_json({"error": "index.html not found"}, 404)
        elif clean_path in ("/ITSROCK.png", "/favicon.ico"):
            if os.path.exists(ICON_FILE):
                with open(ICON_FILE, "rb") as f:
                    body = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "image/png")
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self._write_bytes(body)
            else:
                self.send_json({"error": "ITSROCK.png not found"}, 404)
        elif clean_path == "/api/score":
            self.send_json({"score": read_score()}, 200)
        else:
            self.send_json({"error": "Not found"}, 404)

    def do_POST(self):
        clean_path = self.path.split("?", 1)[0]
        if clean_path == "/api/play":
            try:
                payload = self.read_json_body()
            except (json.JSONDecodeError, UnicodeDecodeError):
                self.send_json({"error": "Invalid JSON body"}, 400)
                return

            player_choice = str(payload.get("choice", "")).lower().strip()
            if player_choice not in WEAPONS:
                self.send_json({"error": "Invalid choice. Choose rock, paper, or scissors."}, 400)
                return

            cpu_choice = random.choice(list(WEAPONS.keys()))
            outcome, message = evaluate_round(player_choice, cpu_choice)
            score = read_score()

            if outcome == "win":
                score["player"] += 1
            elif outcome == "lose":
                score["cpu"] += 1
            else:
                score["draws"] += 1

            write_score(score)
            self.send_json({
                "playerChoice": player_choice,
                "cpuChoice": cpu_choice,
                "outcome": outcome,
                "message": message,
                "score": score,
            }, 200)

        elif clean_path == "/api/reset":
            fresh_score = DEFAULT_SCORE.copy()
            write_score(fresh_score)
            self.send_json({
                "message": "SCORE DATA RESET // AWAITING INPUT",
                "score": fresh_score,
            }, 200)
        else:
            self.send_json({"error": "Not found"}, 404)

    def log_message(self, format, *args):
        print(f"[RockPaperScissors] {self.address_string()} - {format % args}")


if __name__ == "__main__":
    server = ThreadingHTTPServer((HOST, PORT), GameRequestHandler)
    print(f"Rock paper scissors running at http://{HOST}:{PORT} (Press Ctrl+C to stop)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
    finally:
        server.server_close()