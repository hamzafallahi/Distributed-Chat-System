import socket
import threading
import sys
import os
import time

class ChatClient:
    def __init__(self, host='localhost', port=12345):
        self.host = host
        self.port = port
        self.socket = None
        self.nickname = None
        self.running = False
        self.receiving_allowed = threading.Event()
        self.receiving_allowed.set()  # Initially allow receiving
        
    def connect(self):
        """Connect to the chat server"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.port))
            self.running = True
            
            # Authentication (uses blocking recv, no timeout needed)
            if not self.authenticate():
                print("❌ Authentication failed. Disconnecting...")
                sys.exit(1)
            
            # Set timeout for receive loop (prevents blocking forever)
            self.socket.settimeout(0.5)
            
            print(f"✅ Connected to server {self.host}:{self.port}")
            print(f"👤 You are connected as: {self.nickname}")
            self.show_help()
            
            # Start threads
            receive_thread = threading.Thread(target=self.receive_messages, daemon=True)
            send_thread = threading.Thread(target=self.send_messages, daemon=True)
            
            receive_thread.start()
            send_thread.start()
            
            receive_thread.join()
            
        except ConnectionRefusedError:
            print("❌ Cannot connect to server")
            sys.exit(1)
        except Exception as e:
            print(f"❌ Error: {e}")
            sys.exit(1)
    
    def authenticate(self):
        """Authenticate the client with the server"""
        try:
            # Receive username request
            request = self.socket.recv(1024).decode('utf-8')
            
            if request == "USERNAME":
                username = input("Username: ").strip()
                while not username:
                    print("❌ Invalid username")
                    username = input("Username: ").strip()
                
                self.socket.send(username.encode('utf-8'))
                
                # Check server response
                response = self.socket.recv(1024).decode('utf-8')
                
                if response == "ALREADY_CONNECTED":
                    print("❌ This user is already connected!")
                    return False
                elif response == "REFUSED":
                    print("❌ Connection refused")
                    return False
                
                if response == "PASSWORD":
                    password = input("Password: ").strip()
                    self.socket.send(password.encode('utf-8'))
                    
                    # Wait for authentication response
                    auth_response = self.socket.recv(1024).decode('utf-8')
                    
                    if auth_response == "AUTH_SUCCESS":
                        self.nickname = username
                        return True
                    elif auth_response == "AUTH_FAILED":
                        print("❌ Incorrect credentials!")
                        return False
            
            return False
            
        except Exception as e:
            print(f"❌ Error during authentication: {e}")
            return False
    
    def receive_messages(self):
        """Receive messages from the server"""
        while self.running:
            try:
                # Wait if file transfer is happening (receiving_allowed will be cleared)
                self.receiving_allowed.wait()
                
                # Check again if we should stop
                if not self.running:
                    break
                
                try:
                    raw_data = self.socket.recv(4096)
                except socket.timeout:
                    # Timeout is expected, just loop and check event again
                    continue
                    
                if raw_data:
                    # Check for incoming peer-to-peer file transfer (binary)
                    if raw_data.startswith(b"[FILE]INCOMING|"):
                        self.receive_incoming_file(raw_data)
                        continue
                    
                    # Decode as text for normal messages
                    try:
                        message = raw_data.decode('utf-8')
                    except UnicodeDecodeError:
                        continue
                    
                    # Filter out file transfer protocol messages
                    if message.startswith("[FILE]"):
                        # Handle file transfer responses
                        if message == "[FILE]FILE_READY":
                            pass
                        elif message.startswith("[FILE]✅") or message.startswith("[FILE]❌"):
                            print(f"\n{message[6:]}\nYou: ", end="")
                    else:
                        print(f"\n{message}\nYou: ", end="")
                        sys.stdout.flush()
            except ConnectionResetError:
                print("\n🔴 Disconnected from server")
                self.running = False
                break
            except Exception as e:
                if self.running:
                    print(f"\n❌ Connection error: {e}")
                break
    
    def send_messages(self):
        """Send messages to the server"""
        print("\nType your message (or /help for help)")
        
        while self.running:
            try:
                message = input("You: ").strip()
                
                if not message:
                    continue
                    
                if message == "/quit":
                    self.socket.send(message.encode('utf-8'))
                    print("👋 Disconnecting...")
                    self.running = False
                    break
                    
                elif message == "/clear":
                    # Clear the console (works on Windows and Unix)
                    os.system('cls' if os.name == 'nt' else 'clear')
                    continue
                    
                elif message == "/help":
                    self.show_help()
                    continue
                
                elif message.startswith("/file "):
                    # Handle file transfer
                    self.send_file(message)
                    continue
                
                elif message.startswith("/sendfile "):
                    # Handle sending a file to a specific user
                    self.send_file_to_user(message)
                    continue
                
                # Send the message to the server
                self.socket.send(message.encode('utf-8'))
                
            except KeyboardInterrupt:
                print("\n👋 Disconnecting...")
                self.socket.send("/quit".encode('utf-8'))
                self.running = False
                break
            except Exception as e:
                print(f"❌ Send error: {e}")
                break
        
        self.disconnect()
    
    def send_file(self, command):
        """Send a file to the server"""
        try:
            parts = command.split(" ", 1)
            if len(parts) < 2:
                print("❌ Usage: /file <filepath>")
                return
            
            filepath = parts[1].strip()
            
            if not os.path.exists(filepath):
                print(f"❌ File not found: {filepath}")
                return
            
            if not os.path.isfile(filepath):
                print(f"❌ Not a file: {filepath}")
                return
            
            filename = os.path.basename(filepath)
            file_size = os.path.getsize(filepath)
            
            # Pause the receive thread during file transfer
            self.receiving_allowed.clear()
            
            # Give receive thread time to notice and block on the event
            # (it may be in the middle of a recv() call)
            time.sleep(0.6)  # Longer than socket timeout (0.5s)
            
            try:
                # Send file command and wait for response
                self.socket.settimeout(5.0)  # Use longer timeout for handshake
                self.socket.send(f"/file {filename}\n".encode('utf-8'))
                response = self.socket.recv(1024).decode('utf-8').strip()
                self.socket.settimeout(0.5)
                        
                if response != "[FILE]FILE_READY":
                    print(f"❌ Server not ready: {response}")
                    return
                
                # Send file size
                self.socket.settimeout(5.0)
                self.socket.send(f"{file_size}\n".encode('utf-8'))
                ack = self.socket.recv(1024).decode('utf-8').strip()
                self.socket.settimeout(0.5)
                        
                if ack != "[FILE]FILE_SIZE_OK":
                    print("❌ Server did not acknowledge file size")
                    return
                
                # Send file data
                print(f"📤 Uploading {filename} ({file_size} bytes)...")
                with open(filepath, 'rb') as f:
                    sent = 0
                    while sent < file_size:
                        chunk = f.read(4096)
                        if not chunk:
                            break
                        self.socket.send(chunk)
                        sent += len(chunk)
                
                # Wait for confirmation
                self.socket.settimeout(5.0)
                confirm = self.socket.recv(1024).decode('utf-8').strip()
                self.socket.settimeout(0.5)
                        
                if confirm.startswith("[FILE]"):
                    print(f"\n{confirm[6:]}\n")  # Remove [FILE] prefix
                else:
                    print(f"\n{confirm}\n")
            finally:
                # Resume the receive thread
                self.receiving_allowed.set()
            
        except Exception as e:
            print(f"❌ Error sending file: {e}")
    
    def send_file_to_user(self, command):
        """Send a file to a specific user (relayed through the server)"""
        try:
            parts = command.split(" ", 2)
            if len(parts) < 3:
                print("❌ Usage: /sendfile <username> <filepath>")
                return
            
            target_user = parts[1].strip()
            filepath = parts[2].strip()
            
            if not os.path.exists(filepath):
                print(f"❌ File not found: {filepath}")
                return
            
            if not os.path.isfile(filepath):
                print(f"❌ Not a file: {filepath}")
                return
            
            filename = os.path.basename(filepath)
            file_size = os.path.getsize(filepath)
            
            # Pause the receive thread during file transfer
            self.receiving_allowed.clear()
            time.sleep(0.6)
            
            try:
                # Send command and wait for response in one blocking operation
                self.socket.settimeout(5.0)  # Use longer timeout for initial handshake
                self.socket.send(f"/sendfile {target_user} {filename}\n".encode('utf-8'))
                
                response = self.socket.recv(1024).decode('utf-8').strip()
                self.socket.settimeout(0.5)  # Restore normal timeout
                
                if response.startswith("[FILE]❌"):
                    print(f"\n{response[6:]}")
                    return
                
                if response != "[FILE]SENDFILE_READY":
                    print(f"❌ Unexpected response: {response}")
                    return
                
                self.socket.settimeout(5.0)
                self.socket.send(f"{file_size}\n".encode('utf-8'))
                ack = self.socket.recv(1024).decode('utf-8').strip()
                self.socket.settimeout(0.5)
                
                if ack != "[FILE]FILE_SIZE_OK":
                    print("❌ Server did not acknowledge file size")
                    return
                
                print(f"📤 Sending {filename} to {target_user} ({file_size} bytes)...")
                with open(filepath, 'rb') as f:
                    sent = 0
                    while sent < file_size:
                        chunk = f.read(4096)
                        if not chunk:
                            break
                        self.socket.send(chunk)
                        sent += len(chunk)
                
                self.socket.settimeout(5.0)
                confirm = self.socket.recv(1024).decode('utf-8').strip()
                self.socket.settimeout(0.5)
                
                if confirm.startswith("[FILE]"):
                    print(f"\n{confirm[6:]}")
                else:
                    print(f"\n{confirm}")
            finally:
                self.receiving_allowed.set()
            
        except Exception as e:
            print(f"❌ Error sending file: {e}")
    
    def receive_incoming_file(self, initial_data):
        """Receive a file sent by another client (relayed by server)"""
        try:
            # Split header from any binary data that arrived with it
            nl = initial_data.find(b'\\n')
            if nl == -1:
                header_bytes = initial_data
                leftover = b''
            else:
                header_bytes = initial_data[:nl]
                leftover = initial_data[nl + 1:]
            
            header = header_bytes.decode('utf-8')
            # Parse: [FILE]INCOMING|sender|filename|filesize
            parts = header.replace("[FILE]INCOMING|", "").split("|")
            sender = parts[0]
            filename = parts[1]
            file_size = int(parts[2])
            
            print(f"\\n📥 Receiving file '{filename}' from {sender} ({file_size} bytes)...")
            
            # Receive file data
            file_data = leftover
            remaining = file_size - len(leftover)
            while remaining > 0:
                try:
                    chunk = self.socket.recv(min(4096, remaining))
                except socket.timeout:
                    continue
                if not chunk:
                    break
                file_data += chunk
                remaining -= len(chunk)
            
            # Save to Downloads folder
            downloads_dir = os.path.join(os.path.expanduser('~'), 'Downloads')
            if not os.path.exists(downloads_dir):
                downloads_dir = os.path.expanduser('~')
            
            save_path = os.path.join(downloads_dir, f"{sender}_{filename}")
            with open(save_path, 'wb') as f:
                f.write(file_data)
            
            print(f"✅ File saved to: {save_path}")
            print("You: ", end="")
            sys.stdout.flush()
            
        except Exception as e:
            print(f"❌ Error receiving file: {e}")
    
    def show_help(self):
        """Display help"""
        help_text = """
📋 Available commands:
  /help - Show this help
  /quit - Leave the chat
  /list - View connected users
  /msg <username> <message> - Send private message
  /file <filepath> - Upload a file to the server
  /sendfile <username> <filepath> - Send a file directly to a user
  /clear - Clear the screen
        """
        print(help_text)
    
    def disconnect(self):
        """Disconnect properly"""
        self.running = False
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
        print("✅ Disconnected")

def main():
    print("="*50)
    print("🤖 CHAT CLIENT")
    print("="*50)
    
    # Connection configuration
    host = input("Server address [localhost]: ").strip() or "localhost"
    port_input = input("Port [12345]: ").strip()
    port = int(port_input) if port_input else 12345
    
    client = ChatClient(host, port)
    client.connect()

if __name__ == "__main__":
    main()
