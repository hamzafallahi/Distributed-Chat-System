"""
Web-based chat UI — serves as a browser frontend for both client and server modes.
Requires Flask: pip install flask
"""
import socket
import threading
import json
import os
import sys
import time
import queue
import uuid

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(BASE_DIR)
sys.path.insert(0, BASE_DIR)

try:
    from flask import Flask, request, jsonify, send_from_directory
except ImportError:
    print("Flask is required. Install it with:  pip install flask")
    sys.exit(1)

app = Flask(__name__)

# ── Global state (multi-client web app) ──
client_bridges = {}          # session_id -> ClientBridge
client_bridges_lock = threading.Lock()
server_bridge = None


# ═══════════════════════════════════════════
#  CLIENT BRIDGE  –  connects to TCP server
# ═══════════════════════════════════════════
class ClientBridge:
    def __init__(self):
        self.sock = None
        self.running = False
        self.nickname = None
        self.messages = []
        self.msg_lock = threading.Lock()
        self.transfer_event = threading.Event()
        self.transfer_event.set()
        self.users = []
        self.users_lock = threading.Lock()

    # ── helpers ──
    def _add(self, mtype, content):
        with self.msg_lock:
            self.messages.append({"id": len(self.messages), "type": mtype, "content": content})

    def get_messages(self, since=0):
        with self.msg_lock:
            return self.messages[since:], len(self.messages)

    # ── connect & authenticate ──
    def connect(self, host, port, username, password):
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(5)
            self.sock.connect((host, int(port)))

            req = self.sock.recv(1024).decode('utf-8')
            if req != "USERNAME":
                self.sock.close()
                return False, "Unexpected server response"

            self.sock.send(username.encode('utf-8'))
            resp = self.sock.recv(1024).decode('utf-8')

            if resp == "ALREADY_CONNECTED":
                self.sock.close()
                return False, "User already connected"
            if resp == "REFUSED":
                self.sock.close()
                return False, "Connection refused"
            if resp != "PASSWORD":
                self.sock.close()
                return False, f"Unexpected: {resp}"

            self.sock.send(password.encode('utf-8'))
            auth = self.sock.recv(1024).decode('utf-8')
            if auth != "AUTH_SUCCESS":
                self.sock.close()
                return False, "Invalid credentials"

            self.nickname = username
            self.running = True
            self.sock.settimeout(0.5)

            # receive history
            try:
                hist = self.sock.recv(16384).decode('utf-8')
                if hist:
                    self._add("history", hist)
            except socket.timeout:
                pass

            threading.Thread(target=self._recv_loop, daemon=True).start()

            # Request initial user list
            try:
                self.sock.send("/list".encode('utf-8'))
            except Exception:
                pass

            return True, "Connected"

        except ConnectionRefusedError:
            return False, "Cannot connect – is the server running?"
        except Exception as e:
            return False, str(e)

    # ── user tracking ──
    def _update_users(self, msg):
        """Parse join/leave/list messages to keep user list current."""
        if "\U0001f465 Connected users:" in msg:
            parts = msg.split("\U0001f465 Connected users:")
            if len(parts) > 1:
                with self.users_lock:
                    self.users = [u.strip() for u in parts[1].strip().split(",") if u.strip()]
        elif " joined the chat" in msg:
            try:
                name = msg.split(" joined the chat")[0].split()[-1]
                with self.users_lock:
                    if name not in self.users:
                        self.users.append(name)
            except Exception:
                pass
        elif " left the chat" in msg:
            try:
                name = msg.split(" left the chat")[0].split()[-1]
                with self.users_lock:
                    self.users = [u for u in self.users if u != name]
            except Exception:
                pass

    def get_users(self):
        with self.users_lock:
            return list(self.users)

    # ── receive loop ──
    def _recv_loop(self):
        while self.running:
            try:
                self.transfer_event.wait()
                if not self.running:
                    break
                try:
                    msg = self.sock.recv(4096).decode('utf-8')
                except socket.timeout:
                    continue
                if msg:
                    self._update_users(msg)
                    # skip file-protocol noise
                    if msg.startswith("[FILE]"):
                        if msg.startswith("[FILE]\u2705") or msg.startswith("[FILE]\u274c"):
                            self._add("system", msg[6:])
                    else:
                        self._add("message", msg)
                else:
                    self.running = False
                    self._add("system", "Disconnected from server")
            except Exception:
                if self.running:
                    self.running = False
                    self._add("system", "Connection lost")
                break

    # ── send text ──
    def send(self, message):
        if self.running and self.sock:
            try:
                self.sock.send(message.encode('utf-8'))
                return True
            except Exception:
                return False
        return False

    # ── file upload ──
    def upload_file(self, filename, file_data):
        if not self.running:
            return False, "Not connected"

        self.transfer_event.clear()
        time.sleep(0.6)

        try:
            self.sock.send(f"/file {filename}".encode('utf-8'))

            resp = self._recv_wait()
            if resp != "[FILE]FILE_READY":
                return False, f"Server not ready: {resp}"

            self.sock.send(str(len(file_data)).encode('utf-8'))

            ack = self._recv_wait()
            if ack != "[FILE]FILE_SIZE_OK":
                return False, "Server did not acknowledge file size"

            sent = 0
            while sent < len(file_data):
                end = min(sent + 4096, len(file_data))
                self.sock.send(file_data[sent:end])
                sent = end

            confirm = self._recv_wait()
            result = confirm[6:] if confirm.startswith("[FILE]") else confirm
            self._add("system", result)
            return True, result
        except Exception as e:
            return False, str(e)
        finally:
            self.transfer_event.set()

    def _recv_wait(self):
        while True:
            try:
                return self.sock.recv(4096).decode('utf-8')
            except socket.timeout:
                continue

    # ── disconnect ──
    def disconnect(self):
        self.running = False
        if self.sock:
            try:
                self.sock.send("/quit".encode('utf-8'))
                time.sleep(0.1)
                self.sock.close()
            except Exception:
                pass
        self.nickname = None


# ═══════════════════════════════════════════
#  SERVER BRIDGE  –  runs TCP server in-process
# ═══════════════════════════════════════════
class ServerBridge:
    def __init__(self):
        self.server_obj = None
        self.running = False
        self.logs = []
        self.log_lock = threading.Lock()
        self.info_str = ""

    def _log(self, mtype, content):
        with self.log_lock:
            self.logs.append({"id": len(self.logs), "type": mtype, "content": content})

    def get_logs(self, since=0):
        with self.log_lock:
            return self.logs[since:], len(self.logs)

    def start(self, host='0.0.0.0', port=12345):
        if self.running:
            return False, "Server already running"
        try:
            from serveur import ChatServer

            self.server_obj = ChatServer(host, int(port))

            # manual socket setup (skip blocking server_interface)
            self.server_obj.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_obj.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_obj.server_socket.bind((host, int(port)))
            self.server_obj.server_socket.listen(5)

            # patch broadcast to capture events for the dashboard
            orig_broadcast = self.server_obj.broadcast

            def patched_broadcast(message, sender_socket=None, save_history=False, timestamp=None):
                orig_broadcast(message, sender_socket, save_history, timestamp)
                display = f"[{timestamp}] {message}" if timestamp else message
                self._log("message", display)

            self.server_obj.broadcast = patched_broadcast

            self.running = True
            self.info_str = f"Server started on {host}:{port}"
            self._log("system", f"✅ Server started on {host}:{port}")

            threading.Thread(target=self.server_obj.accept_clients, daemon=True).start()
            threading.Thread(target=self._monitor_users, daemon=True).start()

            return True, f"Server started on {host}:{port}"

        except OSError as e:
            if "10048" in str(e) or "Address already in use" in str(e):
                return False, "Port already in use"
            return False, str(e)
        except Exception as e:
            return False, str(e)

    def _monitor_users(self):
        """Poll for user join/leave (supplement to broadcast patch)."""
        last = set()
        while self.running:
            time.sleep(1)
            if not self.server_obj:
                break
            with self.server_obj.lock:
                current = set(self.server_obj.nicknames.values())
            for u in current - last:
                self._log("join", f"🔗 {u} connected")
            for u in last - current:
                self._log("leave", f"👋 {u} disconnected")
            last = current

    def get_users(self):
        if self.server_obj:
            with self.server_obj.lock:
                return list(self.server_obj.nicknames.values())
        return []

    def get_history(self):
        if self.server_obj:
            return self.server_obj.chat_history[-50:]
        return []

    def broadcast_msg(self, message):
        if self.server_obj and self.running:
            self.server_obj.broadcast(f"[SERVER] {message}")
            return True
        return False

    def stop(self):
        if not self.running or not self.server_obj:
            return False
        self.running = False
        with self.server_obj.lock:
            for c in list(self.server_obj.clients):
                try:
                    c.send("🔴 Server shutting down...".encode('utf-8'))
                    c.close()
                except Exception:
                    pass
            self.server_obj.clients.clear()
            self.server_obj.nicknames.clear()
            self.server_obj.connected_users.clear()
        try:
            self.server_obj.server_socket.close()
        except Exception:
            pass
        self._log("system", "🛑 Server stopped")
        return True


# ═══════════════════════════════════════════
#  FLASK ROUTES
# ═══════════════════════════════════════════

@app.route('/')
def index():
    return send_from_directory(os.path.join(BASE_DIR, 'web'), 'index.html')


# ────── Client endpoints ──────

@app.route('/api/client/connect', methods=['POST'])
def api_client_connect():
    data = request.json
    bridge = ClientBridge()
    ok, msg = bridge.connect(
        data.get('host', 'localhost'),
        data.get('port', 12345),
        data['username'],
        data['password']
    )
    if ok:
        session_id = str(uuid.uuid4())
        with client_bridges_lock:
            client_bridges[session_id] = bridge
        return jsonify(success=True, message=msg, nickname=bridge.nickname, session=session_id)
    return jsonify(success=False, message=msg, nickname=None)


def _get_client(sid):
    """Look up a client bridge by session id."""
    with client_bridges_lock:
        return client_bridges.get(sid)


@app.route('/api/client/send', methods=['POST'])
def api_client_send():
    bridge = _get_client(request.json.get('session'))
    if not bridge or not bridge.running:
        return jsonify(success=False, message="Not connected")
    msg = request.json.get('message', '')
    if msg:
        return jsonify(success=bridge.send(msg))
    return jsonify(success=False)


@app.route('/api/client/upload', methods=['POST'])
def api_client_upload():
    sid = request.form.get('session') or request.args.get('session')
    bridge = _get_client(sid)
    if not bridge or not bridge.running:
        return jsonify(success=False, message="Not connected")
    f = request.files.get('file')
    if not f:
        return jsonify(success=False, message="No file provided")
    ok, msg = bridge.upload_file(f.filename, f.read())
    return jsonify(success=ok, message=msg)


@app.route('/api/client/messages')
def api_client_messages():
    bridge = _get_client(request.args.get('session'))
    if not bridge:
        return jsonify(messages=[], next=0, connected=False)
    since = int(request.args.get('since', 0))
    msgs, total = bridge.get_messages(since)
    return jsonify(messages=msgs, next=total, connected=bridge.running)


@app.route('/api/client/users')
def api_client_users():
    bridge = _get_client(request.args.get('session'))
    if not bridge or not bridge.running:
        return jsonify(users=[])
    return jsonify(users=bridge.get_users())


@app.route('/api/client/disconnect', methods=['POST'])
def api_client_disconnect():
    sid = request.json.get('session') if request.json else None
    if sid:
        with client_bridges_lock:
            bridge = client_bridges.pop(sid, None)
        if bridge:
            bridge.disconnect()
    return jsonify(success=True)


# ────── Server endpoints ──────

@app.route('/api/server/start', methods=['POST'])
def api_server_start():
    global server_bridge
    data = request.json or {}
    if server_bridge and server_bridge.running:
        # Allow re-access to the running server dashboard
        return jsonify(success=True, message=server_bridge.info_str, rejoined=True)
    server_bridge = ServerBridge()
    ok, msg = server_bridge.start(
        data.get('host', '0.0.0.0'),
        data.get('port', 12345)
    )
    return jsonify(success=ok, message=msg)


@app.route('/api/server/stop', methods=['POST'])
def api_server_stop():
    if server_bridge:
        server_bridge.stop()
    return jsonify(success=True)


@app.route('/api/server/broadcast', methods=['POST'])
def api_server_broadcast():
    if not server_bridge or not server_bridge.running:
        return jsonify(success=False)
    msg = request.json.get('message', '')
    if msg:
        server_bridge.broadcast_msg(msg)
        return jsonify(success=True)
    return jsonify(success=False)


@app.route('/api/server/users')
def api_server_users():
    users = server_bridge.get_users() if server_bridge else []
    return jsonify(users=users)


@app.route('/api/server/logs')
def api_server_logs():
    if not server_bridge:
        return jsonify(logs=[], next=0, running=False)
    since = int(request.args.get('since', 0))
    logs, total = server_bridge.get_logs(since)
    return jsonify(logs=logs, next=total, running=server_bridge.running)


@app.route('/api/server/history')
def api_server_history():
    history = server_bridge.get_history() if server_bridge else []
    return jsonify(history=history)


@app.route('/api/server/open-uploads', methods=['POST'])
def api_server_open_uploads():
    uploads_dir = os.path.join(BASE_DIR, 'uploads')
    if not os.path.exists(uploads_dir):
        os.makedirs(uploads_dir)
    try:
        os.startfile(uploads_dir)  # Windows
        return jsonify(success=True)
    except AttributeError:
        import subprocess
        subprocess.Popen(['xdg-open', uploads_dir])  # Linux/Mac
        return jsonify(success=True)
    except Exception as e:
        return jsonify(success=False, message=str(e))


# ═══════════════════════════════════════════
if __name__ == '__main__':
    print("=" * 50)
    print("  Chat Web App")
    print("=" * 50)
    print("  Open  http://localhost:5000  in your browser")
    print("=" * 50)
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
