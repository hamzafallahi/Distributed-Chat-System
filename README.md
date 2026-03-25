# Distributed Chat System

A real-time multi-client TCP chat application built with Python sockets and threading. Features user authentication, public/private messaging, file sharing, persistent chat history, a server admin console, and a modern web UI. The console-based client/server runs entirely on the Python standard library, while the web UI requires Flask.

![Repo Views](https://views.whatilearened.today/views/github/hamzafallahi/Distributed-Chat-System.svg)
---

## Table of Contents

- [Features](#features)
- [Prerequisites](#prerequisites)
- [Project Structure](#project-structure)
- [How to Run](#how-to-run)
- [User Management](#user-management)
- [Client Commands](#client-commands)
- [Server Commands](#server-commands)
- [How File Transfer Works](#how-file-transfer-works)
- [Chat History](#chat-history)
- [Architecture & Technical Details](#architecture--technical-details)
- [Configuration](#configuration)
- [Running on Multiple Machines (LAN)](#running-on-multiple-machines-lan)
- [Troubleshooting](#troubleshooting)
- [Security Notes](#security-notes)

---

## Features

| Feature | Description |
|---|---|
| **User Authentication** | Username/password login from `users.json`. Same user cannot log in twice at the same time. |
| **Public Chat** | Messages are broadcast to every connected client in real time. |
| **Private Messaging** | `/msg <user> <message>` sends a message visible only to the target user. |
| **File Sharing** | `/file <filepath>` uploads any file to the server's `uploads/` directory and notifies all users. `/sendfile <user> <filepath>` sends a file directly to a specific user. |
| **Chat History** | Last 100 messages are persisted in `chat_history.json`. New clients receive the last 20 on connect. |
| **Server Admin Console** | The server operator can list users, broadcast announcements, and shut down gracefully. |
| **Web UI** | Modern browser-based interface with dark/light theme toggle, user list, file upload, and server dashboard. |
| **Multi-Client Sessions** | Web UI supports multiple independent client sessions (one per browser tab). |
| **Timestamps** | Every message is timestamped in `DD Month YYYY HH:MM:SS` format. |
| **Graceful Disconnect** | `/quit` notifies everyone. Server shutdown warns all clients before closing. |
| **Cross-Platform** | Works on Windows, macOS, and Linux. |

---

## Prerequisites

- **Python 3.6+**
- For the console-based client/server: No external packages — uses only the standard library (`socket`, `threading`, `json`, `os`, `sys`, `datetime`).
- For the web UI: Install Flask with `pip install flask`.

---

## Project Structure

```
project system dis/
├── serveur.py            # Chat server — manages connections, auth, messaging, file storage
├── client.py             # Chat client — connects to server, sends/receives messages and files
├── webapp.py             # Flask web UI backend — serves the browser interface and bridges to TCP server
├── users.json            # User credentials database (username + password)
├── chat_history.json     # Persistent message history (auto-created, keeps last 100 messages)
├── uploads/              # Uploaded files are stored here as <username>_<filename> (auto-created)
├── web/
│   └── index.html        # Single-page web UI (dark/light theme, client chat, server dashboard)
└── README.md             # This file
```

---

## How to Run

You have two ways to use the chat system: the original console-based client/server, or the new web UI. Both work seamlessly and can be used together.

### Console Version (Original)

#### 1. Start the Server

Open a terminal in the project folder and run:

```bash
python serveur.py
```

Output:

```
✅ Chat server started on 0.0.0.0:12345
Waiting for connections...

==================================================
Server commands:
  /list - Display connected clients
  /shutdown - Stop the server
  /broadcast <message> - Send message to all
==================================================

server>
```

The server is now listening on **all network interfaces** on port **12345**.

#### 2. Start a Client

Open a **separate** terminal and run:

```bash
python client.py
```

You will be prompted for connection details and credentials:

```
==================================================
🤖 CHAT CLIENT
==================================================
Server address [localhost]:       ← press Enter for localhost
Port [12345]:                     ← press Enter for default port
Username: hamza
Password: 1234
✅ Connected to server localhost:12345
👤 You are connected as: hamza
```

After connecting you'll see the recent chat history and can start typing messages.

#### 3. Connect More Clients

Repeat step 2 in additional terminal windows. Each client must log in with a **different** account — duplicate logins are rejected.

#### 4. Stop Everything

- **Client:** type `/quit` or press `Ctrl+C`.
- **Server:** type `/shutdown` at the `server>` prompt, or press `Ctrl+C`.

### Web UI Version (New)

The web UI provides a modern browser-based interface for both client and server modes. It runs on top of the same TCP server/client system.

#### Requirements

- Install Flask: `pip install flask`

#### 1. Start the Web App

Run the Flask backend:

```bash
python webapp.py
```

Output:

```
==================================================
  Chat Web App
==================================================
  Open  http://localhost:5000  in your browser
==================================================
```

#### 2. Open in Browser

Open http://localhost:5000 in your browser. You'll see a mode selection screen.

#### 3. Choose Server or Client Mode

- **Server Mode:** Click "Server Mode", enter bind host/port (defaults are fine), click "Start Server". The TCP server starts in-process, and you get a dashboard to monitor users, logs, and broadcast messages.
- **Client Mode:** Click "Client Mode", enter server host/port and your credentials, click "Connect". You get a chat interface with user list, file upload, and commands. You can send files directly to specific users by clicking the send file button next to their name in the user list.

#### 4. Multiple Clients

Each browser tab can run its own client session. Open multiple tabs to connect as different users.

#### 5. Stop

- **Client:** Click "Disconnect" in the chat header.
- **Server:** Click "Stop Server" in the dashboard header.

---

## User Management

Users are defined in `users.json`:

```json
{
  "users": [
    { "username": "alice", "password": "password123" },
    { "username": "bob",   "password": "securepass456" },
    { "username": "hamza", "password": "1234" }
  ]
}
```

**To add a new user:** add a new object to the `users` array and **restart the server**.

> ⚠️ Passwords are stored in plain text. This is a demo project — do not use real passwords.

---

## Client Commands

Once connected, just type a message and press Enter to send it to everyone. The following slash commands are also available:

| Command | Description | Example |
|---|---|---|
| `/help` | Show the help menu | `/help` |
| `/quit` | Disconnect from the chat | `/quit` |
| `/list` | List all currently connected users | `/list` |
| `/msg <user> <message>` | Send a private message to one user | `/msg alice hey!` |
| `/file <filepath>` | Upload a file to the server | `/file C:\docs\report.pdf` |
| `/sendfile <user> <filepath>` | Send a file directly to a specific user | `/sendfile alice C:\docs\report.pdf` |
| `/clear` | Clear the terminal screen | `/clear` |

### Examples

```
You: hello everyone!                           ← public message to all
You: /msg alice this is just for you           ← private message
You: /file C:\Users\hamza\Desktop\image.png    ← upload a file
You: /sendfile alice C:\docs\report.pdf         ← send file directly to alice
You: /list                                     ← see who's online
You: /quit                                     ← leave
```

---

## Server Commands

The server has an admin console that runs alongside the chat:

| Command | Description |
|---|---|
| `/list` | Show all connected clients and their count |
| `/broadcast <message>` | Send a `[SERVER]` announcement to every connected client |
| `/shutdown` | Notify all clients and stop the server |

Example:

```
server> /list
👥 Connected clients (2):
  - hamza
  - alice

server> /broadcast Server will restart in 5 minutes
📢 Message broadcasted: Server will restart in 5 minutes

server> /shutdown
🛑 Stopping server...
✅ Server stopped
```

---

## How File Transfer Works

### Uploading to Server (`/file`)

The file transfer uses a custom handshake protocol over the same TCP connection:

```
Client                              Server
  │                                    │
  │──── "/file <filename>" ───────────▸│
  │◄──── "[FILE]FILE_READY" ──────────│
  │──── file size (bytes) ────────────▸│
  │◄──── "[FILE]FILE_SIZE_OK" ────────│
  │──── file data (4 KB chunks) ──────▸│
  │◄──── "[FILE]✅ File uploaded" ─────│
  │                                    │──▸ broadcast notification to all
```

1. Client sends `/file <filename>` to the server.
2. Server responds with `FILE_READY`.
3. Client sends the file size, server acknowledges.
4. Client streams the raw file bytes in 4 KB chunks.
5. Server saves the file to `uploads/<username>_<filename>`.
6. Server confirms to the sender and broadcasts a notification to all other clients.

### Sending to Specific User (`/sendfile`)

For direct file transfer between clients, the server acts as a relay:

```
Client A (sender)                   Server                              Client B (receiver)
  │                                    │                                    │
  │──── "/sendfile <user> <filename>" ▸│                                    │
  │◄──── "[FILE]SENDFILE_READY" ──────│                                    │
  │──── file size ────────────────────▸│                                    │
  │◄──── "[FILE]FILE_SIZE_OK" ────────│                                    │
  │──── file data ────────────────────▸│──── header + data ───────────────▸│
  │◄──── "[FILE]✅ File sent" ─────────│◄──── (receives file) ─────────────│
```

1. Sender initiates with `/sendfile <target_user> <filename>`.
2. Server checks if target is online and responds with `SENDFILE_READY`.
3. Sender sends file size, server acknowledges.
4. Sender streams file data to server.
5. Server forwards the data to the target client with a special header `[FILE]INCOMING|<sender>|<filename>|<size>\n`.
6. Target client receives and saves the file locally (e.g., to Downloads folder).
7. Server confirms to sender.

A `threading.Lock` (`recv_lock`) on the client ensures the receive thread doesn't intercept the file protocol messages during this handshake — without it, the client would freeze.

---

## Chat History

- Stored in `chat_history.json` (auto-created on first run).
- The server keeps the **last 100 messages** in the file.
- When a new client connects, they receive the **last 20 messages** so they can catch up.
- History includes: public messages, join/leave notifications, and file transfer notifications.
- Private messages are **not** saved to history.

---

## Architecture & Technical Details

### Network Architecture

```
┌──────────┐        TCP :12345        ┌──────────────────┐
│ Client 1 │ ◄──────────────────────▸ │                  │
│ (alice)  │                          │   Chat Server    │
├──────────┤        TCP :12345        │   (serveur.py)   │
│ Client 2 │ ◄──────────────────────▸ │                  │
│  (bob)   │                          │  ┌────────────┐  │
├──────────┤        TCP :12345        │  │ users.json │  │
│ Client 3 │ ◄──────────────────────▸ │  │ history    │  │
│ (hamza)  │                          │  │ uploads/   │  │
└──────────┘                          │  └────────────┘  │
                                      └──────────────────┘
```

### Authentication Protocol

```
Client                              Server
  │◄──── "USERNAME" ────────────────│  Server requests username
  │──── username ──────────────────▸│
  │                                 │  Check: is user already connected?
  │◄──── "PASSWORD" ────────────────│  Server requests password
  │──── password ──────────────────▸│
  │                                 │  Verify against users.json
  │◄──── "AUTH_SUCCESS" ────────────│  ✅ Authenticated
  │◄──── chat history ─────────────│  Last 20 messages
  │                                 │──▸ broadcast "X joined the chat!"
```

If authentication fails, the server responds with `AUTH_FAILED`, `ALREADY_CONNECTED`, or `REFUSED` and closes the connection.

### Threading Model

**Server (`serveur.py`):**
| Thread | Purpose |
|---|---|
| Main thread | Admin console (`server>` prompt) |
| Accept thread | Listens for new TCP connections |
| 1 thread per client | Handles authentication, then message loop |

All threads share `clients`, `nicknames`, and `connected_users` — protected by a `threading.Lock`.

**Client (`client.py`):**
| Thread | Purpose |
|---|---|
| Receive thread | Continuously reads messages from the server socket |
| Send thread | Reads user input and sends messages / commands |

A `recv_lock` ensures the receive thread pauses during file transfers so the send thread can perform the file handshake without interference.

### Key Technical Specs

| Parameter | Value |
|---|---|
| Transport protocol | TCP |
| Default port | 12345 |
| Server bind address | `0.0.0.0` (all interfaces) |
| Message buffer size | 1024 bytes |
| File chunk size | 4096 bytes |
| Max saved history | 100 messages |
| History shown on connect | 20 messages |
| Max queued connections | 5 (`listen(5)`) |
| Encoding | UTF-8 |

---

## Configuration

### Change the Port

Edit the default in `serveur.py`:

```python
server = ChatServer(host='0.0.0.0', port=9999)  # change 12345 to any port
```

Clients will be prompted for the port at startup, or you can change the default in `client.py`:

```python
port = int(port_input) if port_input else 9999
```

### Adjust History Limits

In `serveur.py`:

```python
# Max messages saved to file (save_chat_history method)
json.dump(self.chat_history[-100:], ...)   # change -100

# Messages shown to new clients (send_history method)
for entry in self.chat_history[-20:]:      # change -20
```

### Change Upload Directory

In `serveur.py`:

```python
self.uploads_dir = 'uploads'  # change to any path
```

---

## Running on Multiple Machines (LAN)

Both the console version and web UI work across multiple machines on the same network. You have two clean options – both work perfectly with your current code.

### ✅ Option 1 – Single Web Server + Remote Browser (Simplest)

One machine runs everything: the TCP server + the web UI. Any other machine on the network just opens a browser to that machine's IP.

#### On Machine A (the one that will host the chat server + web UI)

Ensure `webapp.py`, `serveur.py`, `users.json`, and the `web/` folder with `index.html` are in the same directory.

Start the web app:

```cmd
python webapp.py
```

Open a browser on Machine A to http://localhost:5000.

Click "Server Mode" → accept the defaults → "Start Server". The TCP server is now listening on port 12345, and the web UI is accessible from other machines.

Find Machine A's local IP (e.g., 192.168.1.100).

#### On Machine B (any other PC)

Open a browser and go to http://192.168.1.100:5000 (the IP of Machine A).

Click "Client Mode".

Enter:

- Host: localhost (or 127.0.0.1 or even 192.168.1.100) – all work, because the TCP server is on the same machine as the web backend.
- Port: 12345
- Your username/password from `users.json`.

Click "Connect".

✅ You are now chatting via the TCP server on Machine A, using the web UI served from Machine A, but displayed in a browser on Machine B.

File transfers work exactly the same – files are saved in `uploads/` on Machine A.

### ✅ Option 2 – Separate Web Clients (Each machine runs its own webapp.py)

If you prefer to run a dedicated web UI locally on each client machine, that also works.

#### On Machine A (TCP server)

Run the TCP server only:

```cmd
python serveur.py
```

(No web UI needed here unless you also want the dashboard.)

#### On Machine B (your client PC)

Run your local webapp.py:

```cmd
python webapp.py
```

Open browser to http://localhost:5000.

Click "Client Mode".

Enter Machine A's IP (e.g., 192.168.1.100) and port 12345, authenticate.

This is the classic client-server separation – the web UI and the client bridge run locally, but the TCP server is remote.

### 🔥 Which one should you use?

| Scenario | Option 1 | Option 2 |
|---|---|---|
| You want to only run one Python process on the server machine | ✅ Perfect | ❌ Requires both `serveur.py` and `webapp.py` running separately |
| Multiple clients need to chat | ✅ One browser tab per client, all served from the same machine | ✅ Each client runs its own `webapp.py` (more processes) |
| You want the server dashboard (user list, logs, broadcast) | ✅ Yes – Server Mode provides the dashboard | ❌ Dashboard is only available if you also run `webapp.py` on the server |
| File uploads | ✅ All files saved on Machine A | ✅ All files saved on Machine A (remote server) |
| Ease of setup | One-click server start via web UI | Manual start of `serveur.py` on remote machine |

Both work seamlessly with your existing code. Choose Option 1 if you want the simplest deployment – you only need to start one Python script on one machine, and everyone else just opens a browser.

---

## Troubleshooting

| Problem | Cause | Solution |
|---|---|---|
| `Cannot connect to server` | Server not running or wrong IP/port | Make sure `serveur.py` is running. Check the address and port. |
| `This user is already connected!` | Duplicate login | `/quit` from the other session first, or use a different account. |
| `Incorrect credentials!` | Wrong username or password | Check `users.json`. Credentials are case-sensitive. |
| Client freezes during `/file` | Race condition (old client code) | Make sure `client.py` has the `recv_lock` fix — the receive thread must pause during file transfer. |
| `File not found` | Wrong path | Use the full absolute path. Verify the file exists. |
| `Address already in use` on server | Port still held by a previous run | Wait a few seconds, or kill the old process: `netstat -ano \| findstr :12345` then `taskkill /PID <pid> /F`. |
| Connection suddenly drops | Network issue or server shut down | Restart the client. Check if the server is still running. |

---

## Security Notes

⚠️ This is a **demonstration/educational project**. For production use you would need:

- **Encryption**: wrap sockets with SSL/TLS (`ssl` module)
- **Password hashing**: store bcrypt/argon2 hashes instead of plaintext
- **Input validation**: sanitize all user input to prevent injection
- **Rate limiting**: prevent spam/flooding
- **File validation**: restrict allowed file types and maximum sizes
- **Token-based auth**: use JWT or session tokens instead of password-over-wire
