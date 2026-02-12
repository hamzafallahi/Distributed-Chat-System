import socket
import threading
import sys
import json
import os
from datetime import datetime

class ChatServer:
    def __init__(self, host='0.0.0.0', port=12345):
        self.host = host
        self.port = port
        self.server_socket = None
        self.clients = []
        self.nicknames = {}
        self.connected_users = set()  # Track logged-in usernames
        self.lock = threading.Lock()
        self.users_db = self.load_users()
        self.chat_history = self.load_chat_history()
        self.history_file = 'chat_history.json'
        self.uploads_dir = 'uploads'
        self.ensure_uploads_dir()
    
    def load_users(self):
        """Load the user database from users.json"""
        try:
            with open('users.json', 'r') as f:
                data = json.load(f)
                return {user['username']: user['password'] for user in data.get('users', [])}
        except FileNotFoundError:
            print("❌ users.json file not found")
            return {}
        except json.JSONDecodeError:
            print("❌ Error in users.json format")
            return {}
    
    def load_chat_history(self):
        """Load chat history from file"""
        try:
            with open('chat_history.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return []
    
    def save_chat_history(self):
        """Save chat history to file"""
        try:
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(self.chat_history[-100:], f, indent=2, ensure_ascii=False)  # Keep last 100 messages
        except Exception as e:
            print(f"❌ Error saving chat history: {e}")
    
    def ensure_uploads_dir(self):
        """Create uploads directory if it doesn't exist"""
        if not os.path.exists(self.uploads_dir):
            os.makedirs(self.uploads_dir)
            print(f"📁 Created uploads directory: {self.uploads_dir}")
    
    def get_timestamp(self):
        """Get formatted timestamp"""
        now = datetime.now()
        return now.strftime("%d %B %Y %H:%M:%S")
    
    def authenticate_user(self, username, password):
        """Authenticate a user"""
        if username in self.users_db and self.users_db[username] == password:
            return True
        return False
        
    def start(self):
        """Start the chat server"""
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        try:
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            print(f"✅ Chat server started on {self.host}:{self.port}")
            print("Waiting for connections...")
            
            # Thread to accept new connections
            accept_thread = threading.Thread(target=self.accept_clients, daemon=True)
            accept_thread.start()
            
            # Server command interface
            self.server_interface()
            
        except Exception as e:
            print(f"❌ Error: {e}")
            sys.exit(1)
            
    def accept_clients(self):
        """Accept new client connections"""
        while True:
            try:
                client_socket, client_address = self.server_socket.accept()
                print(f"🔗 New connection from {client_address}")
                
                # Start a thread to handle authentication
                thread = threading.Thread(
                    target=self.authenticate_client,
                    args=(client_socket, client_address),
                    daemon=True
                )
                thread.start()
                
            except Exception as e:
                print(f"❌ Connection error: {e}")
                break
    
    def authenticate_client(self, client_socket, client_address):
        """Handle client authentication"""
        try:
            # Request username
            client_socket.send("USERNAME".encode('utf-8'))
            username = client_socket.recv(1024).decode('utf-8').strip()
            
            if not username:
                client_socket.send("REFUSED".encode('utf-8'))
                client_socket.close()
                return
            
            # Check if user is already connected
            with self.lock:
                if username in self.connected_users:
                    client_socket.send("ALREADY_CONNECTED".encode('utf-8'))
                    print(f"❌ Reconnection attempt by {username} (already connected)")
                    client_socket.close()
                    return
            
            # Request password
            client_socket.send("PASSWORD".encode('utf-8'))
            password = client_socket.recv(1024).decode('utf-8').strip()
            
            # Authenticate user
            if self.authenticate_user(username, password):
                with self.lock:
                    self.connected_users.add(username)
                    self.clients.append(client_socket)
                    self.nicknames[client_socket] = username
                
                # Send confirmation
                client_socket.send("AUTH_SUCCESS".encode('utf-8'))
                print(f"✅ {username} authenticated successfully from {client_address}")
                
                # Send chat history to the new user
                self.send_history(client_socket)
                
                # Broadcast join message
                join_msg = f"🚀 {username} joined the chat!"
                timestamp = self.get_timestamp()
                self.broadcast(join_msg, client_socket, save_history=True, timestamp=timestamp)
                
                # Handle this client
                self.handle_client(client_socket)
            else:
                client_socket.send("AUTH_FAILED".encode('utf-8'))
                print(f"❌ Authentication failed for {username} from {client_address}")
                client_socket.close()
                
        except Exception as e:
            print(f"❌ Error during authentication: {e}")
            try:
                client_socket.close()
            except:
                pass
    
    def send_history(self, client_socket):
        """Send chat history to a client"""
        if self.chat_history:
            try:
                history_msg = "\n📜 === Chat History ==="
                for entry in self.chat_history[-20:]:  # Last 20 messages
                    history_msg += f"\n[{entry['timestamp']}] {entry['message']}"
                history_msg += "\n📜 === End of History ===\n"
                client_socket.send(history_msg.encode('utf-8'))
            except Exception as e:
                print(f"❌ Error sending history: {e}")
    
    def handle_client(self, client_socket):
        """Handle messages from a client"""
        nickname = self.nicknames[client_socket]
        
        while True:
            try:
                message = client_socket.recv(1024).decode('utf-8')
                
                if not message:
                    break
                    
                if message.startswith("/"):
                    # Special command
                    if message.startswith("/file "):
                        # Handle file transfer
                        self.handle_file_transfer(client_socket, message)
                    else:
                        self.handle_command(client_socket, message)
                        # /quit already removed the client, stop the loop
                        if message == "/quit":
                            return
                else:
                    # Normal message
                    timestamp = self.get_timestamp()
                    formatted_message = f"{nickname}: {message}"
                    timestamped_message = f"[{timestamp}] {formatted_message}"
                    print(f"💬 {timestamped_message}")
                    self.broadcast(formatted_message, client_socket, save_history=True, timestamp=timestamp)
                    
            except ConnectionResetError:
                break
            except Exception as e:
                print(f"❌ Error with {nickname}: {e}")
                break
        
        # Client disconnected
        self.remove_client(client_socket)
        
    def handle_command(self, client_socket, command):
        """Handle special commands"""
        nickname = self.nicknames[client_socket]
        
        if command == "/quit":
            timestamp = self.get_timestamp()
            self.broadcast(f"👋 {nickname} left the chat", client_socket, save_history=True, timestamp=timestamp)
            self.remove_client(client_socket)
            
        elif command == "/list":
            with self.lock:
                users = ", ".join(self.nicknames.values())
            client_socket.send(f"👥 Connected users: {users}".encode('utf-8'))
            
        elif command == "/help":
            help_text = """
📋 Available commands:
/quit - Leave the chat
/list - View connected users
/help - Show this help
/msg <username> <message> - Send private message
/file <filename> - Send a file
            """
            client_socket.send(help_text.encode('utf-8'))
            
        elif command.startswith("/msg"):
            # Private message
            parts = command.split(" ", 2)
            if len(parts) >= 3:
                target_nickname = parts[1]
                private_message = parts[2]
                self.send_private_message(nickname, target_nickname, private_message)
    
    def handle_file_transfer(self, client_socket, message):
        """Handle file transfer from client"""
        try:
            parts = message.split(" ", 1)
            if len(parts) < 2:
                client_socket.send("❌ Usage: /file <filename>".encode('utf-8'))
                return
            
            filename = parts[1].strip()
            nickname = self.nicknames[client_socket]
            
            # Send ready signal
            client_socket.send("[FILE]FILE_READY".encode('utf-8'))
            
            # Receive file size
            file_size_data = client_socket.recv(1024).decode('utf-8')
            file_size = int(file_size_data)
            
            # Send acknowledgment
            client_socket.send("[FILE]FILE_SIZE_OK".encode('utf-8'))
            
            # Receive file data
            file_data = b""
            remaining = file_size
            while remaining > 0:
                chunk = client_socket.recv(min(4096, remaining))
                if not chunk:
                    break
                file_data += chunk
                remaining -= len(chunk)
            
            # Save file
            safe_filename = os.path.basename(filename)
            filepath = os.path.join(self.uploads_dir, f"{nickname}_{safe_filename}")
            with open(filepath, 'wb') as f:
                f.write(file_data)
            
            # Confirm to sender
            client_socket.send(f"[FILE]✅ File uploaded: {safe_filename}".encode('utf-8'))
            
            # Broadcast file notification
            timestamp = self.get_timestamp()
            file_msg = f"📎 {nickname} sent a file: {safe_filename} ({file_size} bytes)"
            print(f"📎 {filepath} saved ({file_size} bytes)")
            self.broadcast(file_msg, client_socket, save_history=True, timestamp=timestamp)
            
        except Exception as e:
            print(f"❌ File transfer error: {e}")
            try:
                client_socket.send(f"[FILE]❌ File transfer failed: {str(e)}".encode('utf-8'))
            except:
                pass
    
    def send_private_message(self, sender, target, message):
        """Send a private message"""
        with self.lock:
            for sock, nick in self.nicknames.items():
                if nick == target:
                    try:
                        sock.send(f"[PRIVATE from {sender}] {message}".encode('utf-8'))
                        return True
                    except:
                        pass
        return False
    
    def broadcast(self, message, sender_socket=None, save_history=False, timestamp=None):
        """Broadcast a message to all clients"""
        with self.lock:
            # Save to history if needed
            if save_history and timestamp:
                self.chat_history.append({
                    'timestamp': timestamp,
                    'message': message
                })
                self.save_chat_history()
            
            # Add timestamp to message for display (if not a special message)
            display_message = f"[{timestamp}] {message}" if timestamp else message
            
            for client in self.clients:
                if client != sender_socket:
                    try:
                        client.send(display_message.encode('utf-8'))
                    except:
                        # Client disconnected
                        self.remove_client(client)
    
    def remove_client(self, client_socket):
        """Remove a disconnected client"""
        with self.lock:
            if client_socket in self.clients:
                nickname = self.nicknames.get(client_socket, "Unknown")
                print(f"👋 {nickname} disconnected")
                
                self.clients.remove(client_socket)
                if client_socket in self.nicknames:
                    username = self.nicknames[client_socket]
                    del self.nicknames[client_socket]
                    self.connected_users.discard(username)
                
                try:
                    client_socket.close()
                except:
                    pass
    
    def server_interface(self):
        """Server command interface"""
        print("\n" + "="*50)
        print("Server commands:")
        print("  /list - Display connected clients")
        print("  /shutdown - Stop the server")
        print("  /broadcast <message> - Send message to all")
        print("="*50 + "\n")
        
        while True:
            try:
                cmd = input("server> ").strip()
                
                if cmd == "/list":
                    with self.lock:
                        print(f"👥 Connected clients ({len(self.clients)}):")
                        for nick in self.nicknames.values():
                            print(f"  - {nick}")
                            
                elif cmd == "/shutdown":
                    print("🛑 Stopping server...")
                    self.shutdown()
                    break
                    
                elif cmd.startswith("/broadcast"):
                    message = cmd[10:].strip()
                    if message:
                        self.broadcast(f"[SERVER] {message}")
                        print(f"📢 Message broadcasted: {message}")
                        
                elif cmd:
                    print("❌ Unknown command")
                    
            except KeyboardInterrupt:
                print("\n🛑 Stopping server...")
                self.shutdown()
                break
    
    def shutdown(self):
        """Shutdown the server properly"""
        with self.lock:
            for client in self.clients:
                try:
                    client.send("🔴 Server is shutting down. Disconnecting...".encode('utf-8'))
                    client.close()
                except:
                    pass
        
        if self.server_socket:
            self.server_socket.close()
        
        print("✅ Server stopped")
        sys.exit(0)

if __name__ == "__main__":
    server = ChatServer()
    server.start()

