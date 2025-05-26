import traceback
try:
    import socket
    import time
    import random
    import sys
    from config import get_config
    from logger import get_logger

    logger = get_logger("sent_ei")

    def main():
        HOST = get_config('network.ip', '127.0.0.1')
        PORT = get_config('network.port', 5005)
        logger.info(f"Trying to connect to the visualizer at {HOST}:{PORT}")
        logger.info("Make sure the ei_tcp_event_listener.py is running first!")
        sock = None
        try:
            max_retries = 10
            retry_count = 0
            connected = False
            while not connected and retry_count < max_retries:
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(2)
                    sock.connect((HOST, PORT))
                    connected = True
                    logger.info(f"Successfully connected to visualizer")
                except (ConnectionRefusedError, socket.timeout, OSError) as e:
                    retry_count += 1
                    logger.warning(f"Connection attempt {retry_count}/{max_retries} failed: {e}")
                    logger.info(f"Retrying in 2 seconds...")
                    if sock:
                        sock.close()
                    time.sleep(2)
            if not connected:
                logger.error("Could not connect to the visualizer. Make sure ei_tcp_event_listener.py is running.")
                return 1
            sock.settimeout(None)
            try:
                while True:
                    ei = round(random.uniform(5.5, 9.5), 3)
                    try:
                        sock.sendall(f"{ei}\n".encode())
                        logger.info(f"Sent: {ei}")
                        time.sleep(1.5)
                    except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError, OSError) as e:
                        logger.warning(f"Connection to visualizer was closed: {e}")
                        break
            except KeyboardInterrupt:
                logger.info("Shutting down...")
        except Exception as e:
            logger.error(f"Error: {e}")
            traceback.print_exc()
            return 1
        finally:
            if sock:
                try:
                    sock.close()
                    logger.info("Socket closed")
                except:
                    pass
            logger.info("Sender terminated.")
        return 0
    if __name__ == "__main__":
        sys.exit(main())
except Exception as e:
    print("An error occurred:")
    traceback.print_exc()