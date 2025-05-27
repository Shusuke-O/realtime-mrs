#!/usr/bin/env python3
from psychopy import visual, event
import socket
import threading
import time
import sys
import queue

def run_ei_display(win, ei_config, logger, stop_event):
    """
    100% thread-safe E/I Ratio Visualization for persistent PsychoPy window.
    All PsychoPy stimulus creation/updates are done in the main thread.
    The network thread only puts messages on a queue.
    """
    def log(msg):
        if logger:
            logger.info(msg)
        else:
            print(msg, file=sys.stderr)

    HOST = ei_config.get('network_ip', '127.0.0.1')
    PORT = ei_config.get('network_port', 5005)
    initial_radius_pix = ei_config.get('initial_radius_pix', 50)
    circle_fill_color = ei_config.get('circle_fill_color', 'cyan')
    circle_line_color = ei_config.get('circle_line_color', 'white')
    data_timeout_seconds = ei_config.get('data_timeout_seconds', 10)
    text_color = ei_config.get('text_color', 'white')
    text_height_pix = ei_config.get('text_height_pix', 20)

    # Inter-thread communication
    msg_queue = queue.Queue()

    # Create stimuli in main thread
    circle = visual.Circle(win,
        size=initial_radius_pix * 2,
        fillColor=circle_fill_color,
        lineColor=circle_line_color,
        units='pix', pos=(0, 0))
    circle.setAutoDraw(True)
    status = visual.TextStim(win,
        text="E/I: Waiting for client...",
        pos=(0, win.size[1] * 0.4),
        color=text_color, height=text_height_pix, units='pix')
    status.setAutoDraw(True)

    def network_loop():
        server_socket = None
        client_conn = None
        last_data_time = time.time()
        try:
            server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server_socket.bind((HOST, PORT))
            server_socket.listen(1)
            server_socket.settimeout(0.5)
            log(f"[E/I] TCP server listening on {HOST}:{PORT}")
            msg_queue.put(("status", f"E/I: Waiting for client on {HOST}:{PORT}"))
            while not stop_event.is_set():
                if not client_conn:
                    try:
                        client_conn, addr = server_socket.accept()
                        client_conn.settimeout(0.1)
                        log(f"[E/I] Client connected from {addr}")
                        msg_queue.put(("status", f"E/I: Client connected from {addr[0]}"))
                        last_data_time = time.time()
                    except socket.timeout:
                        continue
                else:
                    try:
                        data_bytes = client_conn.recv(1024)
                        if not data_bytes:
                            log("[E/I] Client disconnected.")
                            msg_queue.put(("status", "E/I: Client disconnected. Waiting..."))
                            client_conn.close()
                            client_conn = None
                            continue
                        last_data_time = time.time()
                        try:
                            ei_ratio = float(data_bytes.decode().strip())
                            new_diameter = max(10, int(ei_ratio * 20))
                            msg_queue.put(("circle_size", new_diameter))
                            msg_queue.put(("status", f"E/I Ratio: {ei_ratio:.2f}"))
                        except Exception:
                            log(f"[E/I] Invalid data: {data_bytes}")
                    except socket.timeout:
                        if time.time() - last_data_time > data_timeout_seconds:
                            log("[E/I] Data timeout. Closing client.")
                            msg_queue.put(("status", "E/I: Client timed out. Waiting..."))
                            client_conn.close()
                            client_conn = None
                        continue
                    except Exception as e:
                        log(f"[E/I] Network error: {e}")
                        msg_queue.put(("status", "E/I: Network error. Waiting..."))
                        client_conn.close()
                        client_conn = None
                        continue
        except Exception as e:
            log(f"[E/I] Server error: {e}")
            msg_queue.put(("status", f"E/I: Server error: {e}"))
        finally:
            if client_conn:
                try: client_conn.close()
                except: pass
            if server_socket:
                try: server_socket.close()
                except: pass
            log("[E/I] Network thread finished.")

    net_thread = threading.Thread(target=network_loop, daemon=True)
    net_thread.start()

    try:
        while not stop_event.is_set():
            # Apply any updates from the network thread
            while not msg_queue.empty():
                msg = msg_queue.get_nowait()
                if msg[0] == "status":
                    status.text = msg[1]
                elif msg[0] == "circle_size":
                    circle.size = (msg[1], msg[1])
            keys = event.getKeys(keyList=['escape'])
            if 'escape' in keys:
                log("[E/I] Escape pressed. Stopping task.")
                stop_event.set()
                break
            time.sleep(0.05)
    except Exception as e:
        log(f"[E/I] Main loop error: {e}")
    finally:
        stop_event.set()
        if net_thread.is_alive():
            net_thread.join(timeout=1.0)
        circle.setAutoDraw(False)
        status.setAutoDraw(False)
        log("[E/I] E/I Display Task finished.") 