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
                    message = self.socket.recv(1024).decode('utf-8')
                except socket.timeout:
                    # Timeout is expected, just loop and check event again
                    continue
                    
                if message:
                    # Filter out file transfer protocol messages
                    if message.startswith("[FILE]"):
                        # Handle file transfer responses
                        if message == "[FILE]FILE_READY":
                            # This shouldn't happen here, but just in case
                            pass
                        elif message.startswith("[FILE]✅") or message.startswith("[FILE]❌"):
                            # File transfer result - display it
                            print(f"\n{message[6:]}\nYou: ", end="")  # Remove [FILE] prefix
                        # Don't display other file protocol messages
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
                # Send file command
                self.socket.send(f"/file {filename}".encode('utf-8'))
                
                # Wait for ready signal (with timeout retry)
                response = None
                while not response:
                    try:
                        response = self.socket.recv(1024).decode('utf-8')
                    except socket.timeout:
                        continue
                        
                if response != "[FILE]FILE_READY":
                    print(f"❌ Server not ready: {response}")
                    return
                
                # Send file size
                self.socket.send(str(file_size).encode('utf-8'))
                
                # Wait for acknowledgment (with timeout retry)
                ack = None
                while not ack:
                    try:
                        ack = self.socket.recv(1024).decode('utf-8')
                    except socket.timeout:
                        continue
                        
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
                
                # Wait for confirmation (with timeout retry)
                confirm = None
                while not confirm:
                    try:
                        confirm = self.socket.recv(1024).decode('utf-8')
                    except socket.timeout:
                        continue
                        
                if confirm.startswith("[FILE]"):
                    print(f"\n{confirm[6:]}\n")  # Remove [FILE] prefix
                else:
                    print(f"\n{confirm}\n")
            finally:
                # Resume the receive thread
                self.receiving_allowed.set()
            
        except Exception as e:
            print(f"❌ Error sending file: {e}")
    
    def show_help(self):
        """Display help"""
        help_text = """
📋 Available commands:
  /help - Show this help
  /quit - Leave the chat
  /list - View connected users
  /msg <username> <message> - Send private message
  /file <filepath> - Send a file
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
