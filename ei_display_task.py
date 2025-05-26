#!/usr/bin/env python3
import traceback
from psychopy import visual, core, event
import socket
import threading
import time
import sys


# Config will be passed in, logger will be passed in

def run_ei_display(win, ei_config, logger, stop_event):
    print("[ei_display_task] run_ei_display: Entered function.", file=sys.stderr)
    """
    Manages the E/I ratio display within an existing PsychoPy window.
    Listens for TCP connections and updates the display based on received data.

    Args:
        win: The active PsychoPy window object.
        ei_config: Dictionary containing configuration for the E/I task 
                   (e.g., network_ip, network_port, circle_color, initial_radius).
        logger: Logger instance for task-specific logging.
        stop_event: threading.Event() to signal when to stop the task.
    """
    logger.info("Starting E/I Display Task logic.")
    
    HOST = ei_config.get('network_ip', '127.0.0.1')
    PORT = ei_config.get('network_port', 5005)
    initial_radius_norm = ei_config.get('initial_radius_norm', 0.1) # Radius in 'norm' units
    circle_fill_color = ei_config.get('circle_fill_color', 'blue')
    circle_line_color = ei_config.get('circle_line_color', 'white')
    data_timeout_seconds = ei_config.get('data_timeout_seconds', 10) # Time before assuming client disconnected

    # --- Visual Stimuli (using 'norm' units, ensure window is also using compatible units or convert) ---
    # Assuming PDM window might be 'pix', so we might need to adjust or ensure 'norm' is okay.
    # For now, let's assume 'norm' units as it was in the original. PDM uses 'pix'. This needs to be harmonized.
    # Let's use 'pix' for the circle and make radius configurable in pixels for now.
    initial_radius_pix = ei_config.get('initial_radius_pix', 50) # Radius in pixels
    circle_size_pix = [initial_radius_pix * 2, initial_radius_pix * 2] # width, height for Circle

    # Circle stimulus
    circle = visual.Circle(win, 
                           # radius=initial_radius_pix, # Circle takes radius if units='norm', but size if units='pix'
                           size=initial_radius_pix * 2, # PsychoPy's Circle uses 'size' (diameter) for 'pix' units
                           fillColor=circle_fill_color, 
                           lineColor=circle_line_color, 
                           units='pix', # Explicitly set units
                           pos=(0, 0))
    circle.setAutoDraw(True)

    # Status text
    status_text_stim = visual.TextStim(win, text="E/I Task: Initializing...", 
                                 pos=(0, win.size[1]*0.4), # Position relative to window size
                                 color='white', height=20, units='pix')
    status_text_stim.setAutoDraw(True)
    
    current_stimuli = [circle, status_text_stim]

    server_socket = None
    client_conn = None
    
    # --- TCP Server Thread ---
    # This will run in a separate thread to handle network communication
    # without blocking the PsychoPy draw loop.
    
    network_thread_state = {'connected': False, 'running': True, 'error': None, 'last_data_time': time.time()}
    
    def network_loop():
        nonlocal server_socket, client_conn
        print("[ei_display_task] network_loop: Entered thread.", file=sys.stderr)
        
        try:
            print("[ei_display_task] network_loop: Attempting socket.socket().", file=sys.stderr)
            server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            print("[ei_display_task] network_loop: socket.socket() successful.", file=sys.stderr)

            print("[ei_display_task] network_loop: Attempting server_socket.setsockopt().", file=sys.stderr)
            server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            print("[ei_display_task] network_loop: server_socket.setsockopt() successful.", file=sys.stderr)

            print(f"[ei_display_task] network_loop: Attempting server_socket.bind({HOST}, {PORT}).", file=sys.stderr)
            server_socket.bind((HOST, PORT))
            print("[ei_display_task] network_loop: server_socket.bind() successful.", file=sys.stderr)

            print("[ei_display_task] network_loop: Attempting server_socket.listen().", file=sys.stderr)
            server_socket.listen(1)
            print("[ei_display_task] network_loop: server_socket.listen() successful.", file=sys.stderr)

            print("[ei_display_task] network_loop: Attempting server_socket.settimeout(0.5).", file=sys.stderr)
            server_socket.settimeout(0.5) # Timeout for accept
            print("[ei_display_task] network_loop: server_socket.settimeout() successful.", file=sys.stderr)
            
            logger.info(f"E/I Task: TCP server listening on {HOST}:{PORT}") # This uses the passed logger
            print(f"[ei_display_task] network_loop: TCP server should be listening on {HOST}:{PORT}. Entering accept loop.", file=sys.stderr)
            network_thread_state['last_data_time'] = time.time()

            while network_thread_state['running'] and not stop_event.is_set():
                if not network_thread_state['connected']:
                    # print("[ei_display_task] network_loop: In accept loop, not connected.", file=sys.stderr) # Too verbose for now
                    status_text_stim.text = f"E/I: Waiting for client on {HOST}:{PORT}"
                    try:
                        # print("[ei_display_task] network_loop: Attempting server_socket.accept().", file=sys.stderr) # Too verbose
                        client_conn, addr = server_socket.accept()
                        # print(f"[ei_display_task] network_loop: server_socket.accept() successful, client: {addr}.", file=sys.stderr)
                        client_conn.settimeout(0.1) # Timeout for recv
                        network_thread_state['connected'] = True
                        network_thread_state['last_data_time'] = time.time()
                        logger.info(f"E/I Task: Client connected from {addr}")
                        status_text_stim.text = f"E/I: Client connected from {addr[0]}"
                    except socket.timeout:
                        if stop_event.is_set(): break
                        continue # Go back to check stop_event and re-try accept
                    except Exception as e_accept:
                        if not stop_event.is_set(): # Don't log if we are trying to stop
                           logger.error(f"E/I Task: Error accepting connection: {e_accept}")
                        network_thread_state['error'] = str(e_accept)
                        break 
                else: # Connected
                    try:
                        data_bytes = client_conn.recv(1024)
                        if not data_bytes:
                            logger.info("E/I Task: Client disconnected.")
                            network_thread_state['connected'] = False
                            if client_conn: client_conn.close()
                            client_conn = None
                            status_text_stim.text = "E/I: Client disconnected. Waiting..."
                            continue
                        
                        network_thread_state['last_data_time'] = time.time()
                        try:
                            ei_ratio_str = data_bytes.decode().strip()
                            ei_ratio = float(ei_ratio_str)
                            
                            # Update circle size (example scaling)
                            # The visual.Circle with units='pix' uses 'size' (diameter)
                            new_diameter = max(10, int(ei_ratio * 20)) # Ensure minimum size, scale factor 20
                            circle.size = (new_diameter, new_diameter)
                            
                            status_text_stim.text = f"E/I Ratio: {ei_ratio:.2f}"
                        except ValueError:
                            logger.warning(f"E/I Task: Invalid data received: {ei_ratio_str}")
                        except Exception as e_data_proc:
                            logger.error(f"E/I Task: Error processing data: {e_data_proc}")
                            # Potentially mark as disconnected or handle error
                            
                    except socket.timeout:
                        # Check for data timeout
                        if time.time() - network_thread_state['last_data_time'] > data_timeout_seconds:
                            logger.warning(f"E/I Task: No data from client for {data_timeout_seconds}s. Assuming disconnect.")
                            network_thread_state['connected'] = False
                            if client_conn: client_conn.close()
                            client_conn = None
                            status_text_stim.text = "E/I: Client timed out. Waiting..."
                        if stop_event.is_set(): break
                        continue # Expected due to non-blocking recv
                    except (ConnectionResetError, BrokenPipeError):
                        logger.warning("E/I Task: Client connection lost (reset/broken pipe).")
                        network_thread_state['connected'] = False
                        if client_conn: client_conn.close()
                        client_conn = None
                        status_text_stim.text = "E/I: Client connection lost. Waiting..."
                    except Exception as e_recv:
                        if not stop_event.is_set():
                            logger.error(f"E/I Task: Error receiving data: {e_recv}")
                        network_thread_state['error'] = str(e_recv)
                        network_thread_state['connected'] = False # Assume connection is problematic
                        if client_conn: client_conn.close()
                        client_conn = None
                        break 
            
        except Exception as e_server_setup:
            logger.error(f"E/I Task: CRITICAL - Error in network_loop setup: {e_server_setup}")
            traceback.print_exc()
            network_thread_state['error'] = f"Server setup failed: {e_server_setup}"
        finally:
            network_thread_state['running'] = False
            if client_conn:
                try: client_conn.close()
                except: pass
                print("[ei_display_task] network_loop: Client socket closed in finally.", file=sys.stderr)
            if server_socket:
                try: server_socket.close()
                except: pass
                print("[ei_display_task] network_loop: Server socket closed in finally.", file=sys.stderr)
            logger.info("E/I Task: Network thread finished.")
            print("[ei_display_task] network_loop: Exiting thread (finally block completed).", file=sys.stderr)

    # --- Main Task Loop (in PsychoPy's main thread) ---
    print("[ei_display_task] run_ei_display: Starting network_thread.", file=sys.stderr)
    network_thread = threading.Thread(target=network_loop, daemon=True)
    network_thread.start()
    print("[ei_display_task] run_ei_display: network_thread started.", file=sys.stderr)
    
    logger.info("E/I Task: Display loop started.")
    
    try:
        while not stop_event.is_set():
            if network_thread_state['error']:
                logger.error(f"E/I Task: Network thread critical error: {network_thread_state['error']}")
                # Simplified error handling: Log and break. PDM will eventually take over.
                # The error_display TextStim might be too complex with PDM's main loop also managing flips.
                status_text_stim.text = f"E/I Network Error: {network_thread_state['error']}" # Update status text
                # PDM's main flip will show this. Give it a moment then break.
                time.sleep(1) # Python time.sleep, not core.wait
                break 

            if not network_thread.is_alive() and network_thread_state['running']:
                 logger.warning("E/I Task: Network thread died unexpectedly.")
                 status_text_stim.text = "E/I: Network thread error. Task stopping."
                 time.sleep(1) # Python time.sleep
                 break

            keys = event.getKeys(keyList=['escape'])
            if 'escape' in keys:
                logger.info("E/I Task: Escape key pressed. Signaling stop.")
                stop_event.set()
                break
            
            # The PDM's main loop is handling win.flip() and core.wait().
            # This loop just needs to stay alive and check for stop conditions.
            # A short sleep can prevent this loop from busy-waiting too aggressively if needed,
            # but event.getKeys() or stop_event.wait(timeout) would be better.
            # For now, let PDM's core.wait() manage the main thread's responsiveness.
            # Let's use a short Python time.sleep here to ensure this loop yields.
            time.sleep(0.05) 

    except Exception as e_main:
        logger.error(f"E/I Task: Error in main display loop: {e_main}")
        traceback.print_exc()
    finally:
        logger.info("E/I Task: Cleaning up and stopping...")
        stop_event.set() # Ensure it's set for the network thread

        if network_thread and network_thread.is_alive():
            logger.info("E/I Task: Waiting for network thread to join...")
            network_thread.join(timeout=1.0)
            if network_thread.is_alive():
                logger.warning("E/I Task: Network thread did not join in time.")
        
        for stim in current_stimuli:
            if stim:
                stim.setAutoDraw(False)
        # win.flip() # Clear the stimuli from screen - PDM will handle next screen state (e.g., standby)
        
        logger.info("E/I Display Task: run_ei_display function finished.")
        print("[ei_display_task] run_ei_display: Exiting function (finally block completed).", file=sys.stderr)


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