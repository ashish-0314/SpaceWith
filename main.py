"""
Gemini Screen Assistant
-----------------------
A transparent floating overlay that captures your screen and uses
Google Gemini Vision API to analyze and answer questions about it.

Learning concepts:
- Screen capture with mss + PIL
- Google Gemini multimodal API (vision)
- Tkinter transparent always-on-top overlay
- Hotkey binding with keyboard library
"""

import tkinter as tk
import socket
import sys
import threading

from app.overlay import OverlayApp

_lock_socket = None
_app_instance = None

def listen_for_wakeup():
    """Background thread to listen for wake-up signals from new instances."""
    global _lock_socket, _app_instance
    while True:
        try:
            conn, _ = _lock_socket.accept()
            msg = conn.recv(1024)
            if msg == b"WAKE_UP" and _app_instance:
                # Restore the window using tkinter thread-safe after()
                _app_instance.root.after(0, _app_instance.root.deiconify)
                _app_instance.root.after(0, lambda: _app_instance.root.attributes("-topmost", True))
            conn.close()
        except:
            break

def enforce_single_instance_early():
    """Check if another instance is running BEFORE initializing the app."""
    global _lock_socket
    try:
        _lock_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        _lock_socket.bind(("127.0.0.1", 15432))
        _lock_socket.listen(1)
        
        # We are the primary instance.
        threading.Thread(target=listen_for_wakeup, daemon=True).start()
    except socket.error:
        # Another instance is already bound to the port.
        try:
            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client.connect(("127.0.0.1", 15432))
            client.sendall(b"WAKE_UP")
            client.close()
            print("Woke up the existing Mistral Screen Assistant instance.")
        except Exception as e:
            print(f"Another instance is running, but failed to wake it up: {e}")
        sys.exit(0)

if __name__ == "__main__":
    enforce_single_instance_early()
    
    root = tk.Tk()
    _app_instance = OverlayApp(root)
    root.mainloop()
