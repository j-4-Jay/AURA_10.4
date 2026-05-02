import zmq
import time

# [AURA-STRICT-PROTOCOL] Phase 1 Module 2 - Ping-Pong Latency Test
def run_latency_test(num_ticks=10000, pub_port=5555):
    context = zmq.Context()
    
    # Publisher socket (acting as MT5 sending ticks)
    pub_socket = context.socket(zmq.PUB)
    pub_socket.connect(f"tcp://127.0.0.1:{pub_port}")
    
    print(f"[MT5 SIMULATOR] Connected to ZMQ Bridge on port {pub_port}.")
    print("[MT5 SIMULATOR] Warning: ZMQ needs a brief moment to handshake before broadcasting.")
    time.sleep(1.0) # Give ZMQ SUB socket time to connect
    
    print(f"[MT5 SIMULATOR] Blasting {num_ticks} simulated ticks to Python...")
    start_time = time.time()
    
    for i in range(1, num_ticks + 1):
        message = f"TICK EURUSD 1.0540 1.0542 {i}"
        pub_socket.send_string(message)
    
    # Send a kill signal to easily see when it's done
    time.sleep(0.1) # Small delay to ensure all ticks arrive before kill
    pub_socket.send_string("TICK EURUSD 0.0000 0.0000 DONE")
    
    elapsed = time.time() - start_time
    # Note: 10,000 / 0.05 seconds = 200,000 ticks per second throughput
    print(f"[MT5 SIMULATOR] Test complete in {elapsed:.4f} seconds.")
    print(f"[MT5 SIMULATOR] Average latency: {(elapsed / num_ticks) * 1000:.4f} ms per tick.")
    
    pub_socket.close()
    context.term()

if __name__ == "__main__":
    run_latency_test()