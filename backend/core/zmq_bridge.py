 
import zmq
import time
import json
import threading

# [AURA-STRICT-PROTOCOL] Phase 1 Module 2 - ZMQ Bridge
class AuraZmqBridge:
    def __init__(self, pub_port=5555, req_port=5556):
        self.context = zmq.Context()
        
        # SUB Socket (Listens for incoming Tick Data from MT5)
        self.sub_socket = self.context.socket(zmq.SUB)
        self.sub_socket.bind(f"tcp://*:{pub_port}")
        self.sub_socket.setsockopt_string(zmq.SUBSCRIBE, "") # Listen to all topics
        
        # REP Socket (Listens for Order Requests from MT5)
        self.rep_socket = self.context.socket(zmq.REP)
        self.rep_socket.bind(f"tcp://*:{req_port}")
        
        self.running = False
        print(f"[AURA] ZMQ Bridge Initialized. Listening on ports {pub_port} (SUB) and {req_port} (REP).")

    def listen_ticks(self):
        print("[AURA] Tick Listener thread started.")
        while self.running:
            try:
                # Non-blocking receive
                message = self.sub_socket.recv_string(flags=zmq.NOBLOCK)
                # The expected format from MT5: "TICK EURUSD 1.0540 1.0542"
                print(f"[LIVE TICK] -> {message}")
            except zmq.Again:
                time.sleep(0.001) # Sleep 1ms to prevent CPU pegging
            except Exception as e:
                print(f"[!] Tick Listener Error: {e}")

    def listen_orders(self):
        print("[AURA] Order REP thread started.")
        while self.running:
            try:
                # Blocking receive for orders (we must reply)
                message = self.rep_socket.recv_string()
                print(f"[ORDER REQ] -> {message}")
                
                # Echo back a success message for the Ping-Pong test
                reply = json.dumps({"status": "ACK", "message": f"Received: {message}"})
                self.rep_socket.send_string(reply)
            except Exception as e:
                print(f"[!] Order Listener Error: {e}")

    def start(self):
        self.running = True
        self.tick_thread = threading.Thread(target=self.listen_ticks, daemon=True)
        self.order_thread = threading.Thread(target=self.listen_orders, daemon=True)
        self.tick_thread.start()
        self.order_thread.start()
        
        print("[AURA] Bridge is active. Waiting for MT5 connection... (Press Ctrl+C to stop)")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self.stop()

    def stop(self):
        print("\n[AURA] Shutting down ZMQ Bridge...")
        self.running = False
        self.sub_socket.close()
        self.rep_socket.close()
        self.context.term()

if __name__ == "__main__":
    bridge = AuraZmqBridge()
    bridge.start()