# 🤖 Distributed Chat System

A real-time multi-client chat application built with Python sockets, featuring user authentication, private messaging, file sharing, and persistent chat history.

## 📋 Table of Contents

- [Features](#features)
- [Requirements](#requirements)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [User Credentials](#user-credentials)
- [Available Commands](#available-commands)
- [Project Structure](#project-structure)
- [How It Works](#how-it-works)
- [Configuration](#configuration)
- [Troubleshooting](#troubleshooting)

## ✨ Features

- **User Authentication**: Secure login system with username/password validation
- **Real-time Messaging**: Instant message delivery to all connected clients
- **Private Messaging**: Send direct messages to specific users
- **File Transfer**: Share files with all users in the chat room
- **Chat History**: Persistent storage of messages (last 100 messages)
- **Multiple Clients**: Support for multiple simultaneous connections
- **Duplicate Login Prevention**: One user can only be logged in once
- **User Management**: View list of connected users
- **Command Interface**: Rich set of commands for enhanced functionality
- **Timestamped Messages**: All messages include timestamps

## 🔧 Requirements

- Python 3.6 or higher
- Standard library modules:
  - `socket`
  - `threading`
  - `json`
  - `os`
  - `sys`
  - `datetime`

**No external dependencies required!**

## 📥 Installation

1. **Clone or download the project:**
   ```bash
   cd "c:\Users\hamza\Desktop\project system dis"
   ```

2. **Verify required files are present:**
   ```
   chat_history.json    # Chat history storage
   client.py            # Client application
   serveur.py           # Server application
   users.json           # User database
   uploads/             # File storage directory
   ```

3. **Ensure `users.json` exists** (already included in project)

## 🚀 Quick Start

### Step 1: Start the Server

Open a terminal/command prompt and run:

```bash
python serveur.py
```

You should see:
```
✅ Chat server started on 0.0.0.0:12345
Waiting for connections...
```

### Step 2: Connect Clients

Open **new terminal windows** for each client and run:

```bash
python client.py
```

Follow the prompts:
1. **Server address**: Press Enter for `localhost` (or enter server IP)
2. **Port**: Press Enter for `12345` (default)
3. **Username**: Enter one of the usernames from the table below
4. **Password**: Enter the corresponding password

### Step 3: Start Chatting!

Once connected, you can:
- Type messages directly and press Enter to send
- Use commands (see [Available Commands](#available-commands))
- Send files, private messages, and more!

## 🔐 User Credentials

The following users are pre-configured in `users.json`:

| Username | Password       |
|----------|----------------|
| alice    | password123    |
| bob      | securepass456  |
| hamza    | 1234           |

### Adding New Users

Edit `users.json` and add new entries:

```json
{
  "users": [
    {
      "username": "newuser",
      "password": "newpassword"
    }
  ]
}
```

**Note**: Restart the server after modifying `users.json`.

## 🎮 Available Commands

### Client Commands

| Command | Description | Example |
|---------|-------------|---------|
| `/help` | Display help menu | `/help` |
| `/quit` | Leave the chat | `/quit` |
| `/list` | View connected users | `/list` |
| `/msg <user> <message>` | Send private message | `/msg alice Hello!` |
| `/file <filepath>` | Send a file | `/file C:\docs\report.pdf` |
| `/clear` | Clear the screen | `/clear` |

### Server Commands

When running the server, you can use:

| Command | Description | Example |
|---------|-------------|---------|
| `/list` | Display connected clients | `/list` |
| `/shutdown` | Stop the server | `/shutdown` |
| `/broadcast <message>` | Send message to all users | `/broadcast Server maintenance in 5 minutes` |

## 📁 Project Structure

```
project system dis/
│
├── serveur.py              # Server application (handles connections, authentication, messaging)
├── client.py               # Client application (connect, send/receive messages)
├── users.json              # User database (usernames and passwords)
├── chat_history.json       # Persistent chat history (last 100 messages)
├── uploads/                # Directory for uploaded files
│   └── [user]_[filename]   # Format: username_originalfilename
└── README.md               # This file
```

## 🔍 How It Works

### Architecture

```
┌─────────────┐         ┌─────────────┐         ┌─────────────┐
│   Client 1  │◄───────►│             │◄───────►│   Client 2  │
│  (alice)    │         │   Server    │         │    (bob)    │
└─────────────┘         │             │         └─────────────┘
                        │  - Auth     │
┌─────────────┐         │  - Routing  │         ┌─────────────┐
│   Client 3  │◄───────►│  - History  │◄───────►│   Client N  │
│  (hamza)    │         │  - Files    │         │   (...)     │
└─────────────┘         └─────────────┘         └─────────────┘
```

### Connection Flow

1. **Client connects** to server (default: localhost:12345)
2. **Server requests** username
3. **Server checks** if username is already logged in
4. **Server requests** password
5. **Server authenticates** against `users.json`
6. **Server sends** chat history to new client
7. **Server broadcasts** join notification
8. **Client can send/receive** messages and files

### Message Flow

- **Public messages**: Broadcast to all connected clients
- **Private messages**: Delivered only to specified recipient
- **File transfers**: Binary data transfer with size verification
- **System messages**: Join/leave notifications

### Threading Model

- **Server**: 
  - Main thread: Command interface
  - Accept thread: New connections
  - Client threads: One per connected client
  
- **Client**:
  - Main thread: User input
  - Receive thread: Incoming messages
  - Send thread: Outgoing messages

## ⚙️ Configuration

### Change Server Port

**In `serveur.py`:**
```python
server = ChatServer(host='0.0.0.0', port=12345)  # Change port here
```

**In `client.py`:**
```python
# User will be prompted, or set default:
port = int(port_input) if port_input else 12345  # Change default here
```

### Change Server Host

For remote connections, run server with:
```python
server = ChatServer(host='0.0.0.0', port=12345)  # Accepts all connections
```

Clients connect using server's IP address:
```
Server address: 192.168.1.100  # Replace with actual server IP
```

### Adjust Chat History Limit

**In `serveur.py`, modify:**
```python
json.dump(self.chat_history[-100:], f, ...)  # Change -100 to desired limit
```

### File Upload Directory

**In `serveur.py`:**
```python
self.uploads_dir = 'uploads'  # Change directory name here
```

## 🐛 Troubleshooting

### "Cannot connect to server"

**Cause**: Server is not running or wrong host/port

**Solution**: 
- Verify server is running: `python serveur.py`
- Check host/port settings match
- Ensure firewall allows the connection

### "This user is already connected!"

**Cause**: User is logged in from another client

**Solution**: 
- Logout from other client first (`/quit`)
- Use a different username
- Restart the server (clears all connections)

### "Authentication failed"

**Cause**: Incorrect username or password

**Solution**:
- Verify credentials in `users.json`
- Check for typos (case-sensitive)
- Ensure no extra spaces in input

### "File not found"

**Cause**: Incorrect file path

**Solution**:
- Use absolute path: `/file C:\full\path\to\file.txt`
- Use quotes for paths with spaces: `/file "C:\My Documents\file.txt"`
- Verify file exists before sending

### Port Already in Use

**Cause**: Server already running or port occupied

**Solution**:
```bash
# Windows - find process using port 12345
netstat -ano | findstr :12345

# Kill process by PID
taskkill /PID <PID> /F
```

### Connection Suddenly Drops

**Cause**: Network issue or server shutdown

**Solution**:
- Check network connection
- Restart client and reconnect
- Verify server is still running

## 🔒 Security Notes

⚠️ **Important**: This is a demonstration project. For production use:

- Implement encryption (SSL/TLS)
- Use hashed passwords (not plaintext in `users.json`)
- Add input validation and sanitization
- Implement rate limiting
- Add proper error handling for malicious input
- Validate file types and sizes before upload
- Use secure authentication methods (tokens, OAuth, etc.)

## 📝 Example Usage

### Basic Chat Session

```
Client 1 (alice):
> Username: alice
> Password: password123
✅ Connected to server localhost:12345
👤 You are connected as: alice
You: Hello everyone!

Client 2 (bob):
> Username: bob
> Password: securepass456
✅ Connected to server localhost:12345
[01 February 2026 15:10:55] alice: Hello everyone!
You: Hi alice!
```

### Private Message

```
Client (alice):
You: /msg bob This is a private message
[Private to bob] This is a private message

Client (bob):
[Private from alice] This is a private message
```

### File Transfer

```
Client (alice):
You: /file C:\documents\report.pdf
📤 Uploading report.pdf (2048 bytes)...
✅ File uploaded: report.pdf

All clients see:
📎 alice sent a file: report.pdf (2048 bytes)
```

## 👥 Contributing

To add new features:

1. Fork/modify the code
2. Test with multiple clients
3. Update this README
4. Document any new commands or features

## 📄 License

This project is for educational purposes.

## 👤 Author

Created as a distributed systems project.

---

**Happy Chatting! 💬**
