#!/usr/bin/env python3
import traceback
from psychopy import visual, event, core
import socket
import threading
import time
import sys
import signal

def run_ei_display(win, ei_config, logger, stop_event):
    """
    Minimal, robust E/I Ratio Visualization for use with a persistent PsychoPy window.
    All PsychoPy stimulus creation/updates are scheduled with win.callOnFlip.
    """
    logger.info("[E/I] Starting minimal E/I Display Task logic.")
    HOST = ei_config.get('network_ip', '127.0.0.1')
    PORT = ei_config.get('network_port', 5005)
    initial_radius_pix = ei_config.get('initial_radius_pix', 50)
    circle_fill_color = ei_config.get('circle_fill_color', 'cyan')
    circle_line_color = ei_config.get('circle_line_color', 'white')
    data_timeout_seconds = ei_config.get('data_timeout_seconds', 10)
    text_color = ei_config.get('text_color', 'white')
    text_height_pix = ei_config.get('text_height_pix', 20)

    # Shared state for main and network thread
    state = {'circle': None, 'status': None, 'stim_ready': threading.Event()}

    def create_stimuli():
        state['circle'] = visual.Circle(win,
            size=initial_radius_pix * 2,
            fillColor=circle_fill_color,
            lineColor=circle_line_color,
            units='pix', pos=(0, 0))
        state['circle'].setAutoDraw(True)
        state['status'] = visual.TextStim(win,
            text="E/I: Waiting for client...",
            pos=(0, win.size[1] * 0.4),
            color=text_color, height=text_height_pix, units='pix')
        state['status'].setAutoDraw(True)
        state['stim_ready'].set()
    win.callOnFlip(create_stimuli)

    def cleanup_stimuli():
        if state['circle']:
            state['circle'].setAutoDraw(False)
        if state['status']:
            state['status'].setAutoDraw(False)
    
    def set_status(text):
        def _set():
            if state['status']:
                state['status'].text = text
        win.callOnFlip(_set)

    def set_circle_size(diameter):
        def _set():
            if state['circle']:
                state['circle'].size = (diameter, diameter)
        win.callOnFlip(_set)

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
            logger.info(f"[E/I] TCP server listening on {HOST}:{PORT}")
            set_status(f"E/I: Waiting for client on {HOST}:{PORT}")
            while not stop_event.is_set():
                if not client_conn:
                    try:
                        client_conn, addr = server_socket.accept()
                        client_conn.settimeout(0.1)
                        logger.info(f"[E/I] Client connected from {addr}")
                        set_status(f"E/I: Client connected from {addr[0]}")
                        last_data_time = time.time()
                    except socket.timeout:
                        continue
                else:
                    try:
                        data_bytes = client_conn.recv(1024)
                        if not data_bytes:
                            logger.info("[E/I] Client disconnected.")
                            set_status("E/I: Client disconnected. Waiting...")
                            client_conn.close()
                            client_conn = None
                            continue
                        last_data_time = time.time()
                        try:
                            ei_ratio = float(data_bytes.decode().strip())
                            new_diameter = max(10, int(ei_ratio * 20))
                            set_circle_size(new_diameter)
                            set_status(f"E/I Ratio: {ei_ratio:.2f}")
                        except Exception:
                            logger.warning(f"[E/I] Invalid data: {data_bytes}")
                    except socket.timeout:
                        if time.time() - last_data_time > data_timeout_seconds:
                            logger.warning("[E/I] Data timeout. Closing client.")
                            set_status("E/I: Client timed out. Waiting...")
                            client_conn.close()
                            client_conn = None
                        continue
                    except Exception as e:
                        logger.error(f"[E/I] Network error: {e}")
                        set_status("E/I: Network error. Waiting...")
                        client_conn.close()
                        client_conn = None
                        continue
        except Exception as e:
            logger.error(f"[E/I] Server error: {e}")
            set_status(f"E/I: Server error: {e}")
        finally:
            if client_conn:
                try: client_conn.close()
                except: pass
            if server_socket:
                try: server_socket.close()
                except: pass
            logger.info("[E/I] Network thread finished.")

    # Wait for stimuli to be created before starting network
    while not state['stim_ready'].is_set() and not stop_event.is_set():
        time.sleep(0.01)

    net_thread = threading.Thread(target=network_loop, daemon=True)
    net_thread.start()

    try:
        while not stop_event.is_set():
            keys = event.getKeys(keyList=['escape'])
            if 'escape' in keys:
                logger.info("[E/I] Escape pressed. Stopping task.")
                stop_event.set()
                break
            time.sleep(0.05)
    except Exception as e:
        logger.error(f"[E/I] Main loop error: {e}")
        traceback.print_exc()
    finally:
        stop_event.set()
        if net_thread.is_alive():
            net_thread.join(timeout=1.0)
        win.callOnFlip(cleanup_stimuli)
        logger.info("[E/I] E/I Display Task finished.")


if __name__ == '__main__':
    # --- Standalone Test ---
    print("Running E/I Display Task in standalone test mode...")
    import logging
    test_logger = logging.getLogger("ei_display_test")
    test_logger.addHandler(logging.StreamHandler(sys.stdout)) # Log to stdout for testing
    test_logger.setLevel(logging.INFO)

    # Example config for testing
    test_ei_config = {
        'network_ip': '127.0.0.1',
        'network_port': 5005,
        'initial_radius_pix': 60,
        'circle_fill_color': 'green',
        'data_timeout_seconds': 7
    }
    test_logger.info(f"E/I Test mode using config: {test_ei_config}")

    test_win = None
    _stop_event = threading.Event()

    def signal_handler(sig, frame):
        print('You pressed Ctrl+C!')
        _stop_event.set()

    signal.signal(signal.SIGINT, signal_handler) # Python's signal, not PsychoPy's event

    try:
        # For standalone, PsychoPy window units are important. PDM is 'pix'.
        test_win = visual.Window(size=(800, 600), color='darkgrey', units='pix', fullscr=False)
        test_win.mouseVisible = False
        
        # Simulate PDM's behavior: show message then run task
        intro_msg = visual.TextStim(test_win, "Standalone Test: Starting E/I Task in 2s...", color='white')
        intro_msg.draw()
        test_win.flip()
        core.wait(2)

        run_ei_display(test_win, test_ei_config, test_logger, _stop_event)
        
        # Simulate PDM showing standby after task
        standby_msg = visual.TextStim(test_win, "Standalone Test: E/I Task Ended. Closing.", color='white')
        standby_msg.draw()
        test_win.flip()
        core.wait(2)

    except Exception as e_test:
        test_logger.error(f"Error in E/I standalone test: {e_test}")
        test_logger.error(traceback.format_exc())
    finally:
        if test_win:
            test_win.close()
        core.quit()
        print("E/I Display Task standalone test finished.") 