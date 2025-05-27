#!/usr/bin/env python3
"""
PsychoPy Display Manager
Manages a single, persistent PsychoPy window for displaying instructions,
standby messages, and eventually, task stimuli.
It receives commands via stdin in JSON format.
"""
import sys
import json
import threading
from psychopy import visual, core, event
import traceback
import queue # For thread-safe command queue
import socket  # Added for E/I network server
import time    # Added for E/I network server

# --- Potentially import task-specific configurations or utilities ---
from config import get_config # Assuming this is your central config loader
from logger import get_logger # Assuming this is your central logger getter

# --- Import task functions ---
from m1_tapping_task import run_m1_experiment
from v1_orientation_task import run_v1_experiment # Added V1 import

# Initialize logger for psychopy_display_manager
logger = get_logger("PsychoPyDisplayManager") # Added logger initialization

# --- Configuration ---
DEFAULT_WINDOW_SIZE = [800, 600]
DEFAULT_TEXT_COLOR = 'white'
DEFAULT_BG_COLOR = 'black'
STANDBY_TEXT = "Standby. Please wait for task selection."
INSTRUCTION_PROMPT = "\n\n(Press Enter to continue)"

# --- Global Variables ---
win = None
current_stim = [] # General stimuli managed directly by PDM (text, standby)
keep_running = True
input_thread = None
command_queue = queue.Queue() # Thread-safe queue for commands

# --- E/I Display Management Globals ---
ei_display_active = False
ei_msg_queue = queue.Queue()
ei_circle = None
ei_status = None
ei_network_thread = None
ei_stop_event = None

def setup_psychopy_window():
    """Initializes the PsychoPy window."""
    global win
    try:
        print("PsychoPy Display Manager: Attempting to setup window.", file=sys.stderr)
        win = visual.Window(
            size=DEFAULT_WINDOW_SIZE,
            fullscr=False,  # Set to True for fullscreen
            color=DEFAULT_BG_COLOR,
            units="pix"
        )
        win.mouseVisible = False
        print("PsychoPy Display Manager: Window setup successful.", file=sys.stderr)
        return True
    except Exception as e:
        print(f"CRITICAL: Error initializing PsychoPy window: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        return False

def clear_screen():
    """Clears all current stimuli from the screen."""
    global current_stim, win
    if not win:
        print("PsychoPy Display Manager: clear_screen called but no window.", file=sys.stderr)
        return
    for stim in current_stim:
        stim.setAutoDraw(False)
    current_stim = []
    try:
        win.flip()
    except Exception as e:
        print(f"PsychoPy Display Manager: Error flipping window in clear_screen: {e}", file=sys.stderr)

def show_message(text_content, add_prompt=False):
    """Displays a message on the screen."""
    global win
    if not win:
        print("PsychoPy Display Manager: show_message called but no window.", file=sys.stderr)
        return
    clear_screen()
    actual_text_content = text_content
    if add_prompt:
        actual_text_content += INSTRUCTION_PROMPT
    
    text_stim = visual.TextStim(
        win,
        text=actual_text_content,
        color=DEFAULT_TEXT_COLOR,
        height=24,
        wrapWidth=win.size[0] * 0.8
    )
    text_stim.setAutoDraw(True)
    current_stim.append(text_stim)
    try:
        win.flip()
    except Exception as e:
        print(f"PsychoPy Display Manager: Error flipping window in show_message: {e}", file=sys.stderr)

def handle_command(command_data):
    """Handles a command received from stdin."""
    global keep_running, win, ei_display_active
    if not win:
        print("PsychoPy Display Manager: handle_command called but no window.", file=sys.stderr)
        return

    try:
        action = command_data.get("action")
        print(f"PsychoPy Display Manager: Received command: {action} with data: {command_data}", file=sys.stderr)

        if action == "show_text":
            text = command_data.get("content", "No content provided.")
            wait_for_enter = command_data.get("wait_for_enter", False)
            show_message(text, add_prompt=wait_for_enter)
            if wait_for_enter:
                print("PsychoPy Display Manager: Waiting for Enter key press...", file=sys.stderr)
                event.clearEvents()
                while True:
                    if not keep_running: break
                    keys = event.getKeys(keyList=['return', 'escape'])
                    if 'return' in keys:
                        print("PsychoPy Display Manager: Enter key pressed.", file=sys.stderr)
                        break
                    if 'escape' in keys:
                        print("PsychoPy Display Manager: Escape key pressed during wait_for_enter.", file=sys.stderr)
                        break
                    try:
                        win.flip()
                    except Exception as e:
                        print(f"PsychoPy Display Manager: Error flipping window in wait_for_enter loop: {e}", file=sys.stderr)
                        keep_running = False # If flip fails, better to stop
                        break
                    core.wait(0.01)
                if keep_running:
                    clear_screen()
                print("PsychoPy Display Manager: Finished wait_for_enter.", file=sys.stderr)

        elif action == "show_standby":
            show_message(STANDBY_TEXT)
        elif action == "clear_screen":
            clear_screen()
        elif action == "exit":
            print("PsychoPy Display Manager: Exit command received. Shutting down.", file=sys.stderr)
            keep_running = False
        elif action == "run_m1_task":
            logger.info("PsychoPy Display Manager: Received run_m1_task command.")
            try:
                show_message("Starting M1 Tapping Task...", add_prompt=False)
                core.wait(0.5)
                clear_screen()
                win.flip()

                m1_config_params = {
                    'controller_type': get_config('m1_task.controller', 'keyboard'),
                    'joystick_device': get_config('m1_task.joystick_device', ""),
                    'repetitions': get_config('m1_task.repetitions', 3),
                    'base_sequence': get_config('m1_task.sequence', ['4', '1', '3', '2', '4']),
                    'sequence_display_time': get_config('m1_task.sequence_display_time', 2),
                    'response_cutoff_time': get_config('m1_task.response_cutoff_time', 5),
                    'randomize_sequence': get_config('m1_task.randomize_sequence', False)
                }
                logger.info(f"PsychoPy Display Manager: M1 Task Config loaded: {m1_config_params}")

                run_m1_experiment(win, m1_config_params, logger) # Pass PDM's logger
                
                logger.info("PsychoPy Display Manager: M1 Task function finished.")
                # After task is done, PDM shows completion then standby by putting commands on its own queue.
                command_queue.put({"action": "show_text", "content": "M1 Task Complete.", "wait_for_enter": False})
                command_queue.put({"action": "show_standby"})

            except Exception as e_task:
                error_message_task = f"Error during M1 task execution: {e_task}"
                logger.error(f"PsychoPy Display Manager: {error_message_task}")
                traceback.print_exc(file=sys.stderr)
                # Show error on screen and then go to standby by putting commands on queue
                command_queue.put({"action": "show_text", "content": error_message_task, "wait_for_enter": False})
                command_queue.put({"action": "show_standby"})
        elif action == "run_v1_task":
            logger.info("PsychoPy Display Manager: Received run_v1_task command.")
            try:
                show_message("Starting V1 Orientation Task...", add_prompt=False)
                core.wait(0.5)
                clear_screen()
                win.flip()

                # Configuration for V1 task
                v1_config_params = {
                    'stimulus_duration': get_config('v1_task.stimulus_duration', 0.1),
                    'n_trials': get_config('v1_task.n_trials', 20), # Example: make n_trials configurable
                    'participant_id': get_config('global.participant_id', 'default_p'), # Example: get participant from global config
                    'session_id': get_config('global.session_id', 's001'), # Example: get session from global config
                    'response_cutoff_time': get_config('v1_task.response_cutoff_time', 3) # Default to 3s if not in config
                }
                logger.info(f"PsychoPy Display Manager: V1 Task Config loaded: {v1_config_params}")

                run_v1_experiment(win, v1_config_params, logger) # Pass PDM's logger
                
                logger.info("PsychoPy Display Manager: V1 Task function finished.")
                command_queue.put({"action": "show_text", "content": "V1 Orientation Task Complete.", "wait_for_enter": False})
                command_queue.put({"action": "show_standby"})

            except Exception as e_task:
                error_message_task = f"Error during V1 task execution: {e_task}"
                logger.error(f"PsychoPy Display Manager: {error_message_task}")
                traceback.print_exc(file=sys.stderr)
                command_queue.put({"action": "show_text", "content": error_message_task, "wait_for_enter": False})
                command_queue.put({"action": "show_standby"})
        elif action == "run_ei_task":
            logger.info("PsychoPy Display Manager: Received run_ei_task command.")
            if ei_display_active:
                logger.warning("E/I display already active – ignoring duplicate start command.")
                return

            # Brief on-screen status then start task
            clear_screen()
            show_message("Starting E/I Ratio Visualization Task...", add_prompt=False)
            core.wait(0.5)
            clear_screen()
            win.flip()

            try:
                ei_task_config = {
                    'network_ip': get_config('network.ip', '127.0.0.1'),
                    'network_port': get_config('network.port', 5005),
                    'initial_radius_pix': get_config('ei_task.initial_radius_pix', 50),
                    'circle_fill_color': get_config('ei_task.circle_fill_color', 'cyan'),
                    'circle_line_color': get_config('ei_task.circle_line_color', 'white'),
                    'data_timeout_seconds': get_config('ei_task.data_timeout_seconds', 10),
                    'text_color': get_config('ei_task.text_color', 'white'),
                    'text_height_pix': get_config('ei_task.text_height_pix', 20)
                }
                logger.info(f"PsychoPy Display Manager: E/I Task Config loaded: {ei_task_config}")

                _start_ei_display_task(ei_task_config)

            except Exception as e_task_setup:
                error_message_task_setup = f"Error setting up E/I display: {e_task_setup}"
                logger.error(error_message_task_setup)
                traceback.print_exc(file=sys.stderr)
                command_queue.put({"action": "show_text", "content": error_message_task_setup, "wait_for_enter": False})
                command_queue.put({"action": "show_standby"})

        elif action == "stop_ei_task":
            logger.info("PsychoPy Display Manager: Received stop_ei_task command.")
            _stop_ei_display_task()
            clear_screen()
            command_queue.put({"action": "show_text", "content": "E/I Task Stopped.", "wait_for_enter": False})
            core.wait(0.1)
            command_queue.put({"action": "show_standby"})

        else:
            print(f"PsychoPy Display Manager: Unknown command: {action}", file=sys.stderr)
    except Exception as e:
        print(f"CRITICAL: Error in handle_command with data '{command_data}': {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        keep_running = False

def read_commands():
    """Reads commands from stdin in a separate thread."""
    global keep_running
    print("PsychoPy Display Manager: Input thread (read_commands) started.", file=sys.stderr)
    for line in sys.stdin:
        if not keep_running:
            print("PsychoPy Display Manager: keep_running is false, stopping command reading.", file=sys.stderr)
            break
        try:
            command_str = line.strip()
            if not command_str: # Skip empty lines if any
                continue
            # print(f"PsychoPy Display Manager: Raw command received: {command_str}", file=sys.stderr) # Less verbose
            command = json.loads(command_str)
            # core.callOnNextFlip(handle_command, command_data=command) # Replaced with queue
            command_queue.put(command) # Put command on the queue
        except json.JSONDecodeError:
            print(f"PsychoPy Display Manager: Invalid JSON received: {line.strip()}", file=sys.stderr)
        except Exception as e:
            print(f"PsychoPy Display Manager: Error processing command in read_commands: {e}", file=sys.stderr)
            traceback.print_exc(file=sys.stderr)
            # Don't set keep_running = False here, let main_loop decide or specific commands.
    
    print("PsychoPy Display Manager: stdin closed or keep_running became false. Exiting read_commands.", file=sys.stderr)
    keep_running = False # Ensure main loop stops if stdin closes or after loop finishes

def main_loop():
    """Main PsychoPy event loop."""
    global keep_running, input_thread, win

    if not setup_psychopy_window():
        print("CRITICAL: PsychoPy window setup failed. Exiting Display Manager.", file=sys.stderr)
        return

    print("PsychoPy Display Manager: Window setup complete.", file=sys.stderr)
    show_message("PsychoPy Display Manager Initialized.\nWaiting for commands...")
    print("PsychoPy Display Manager: Initial message shown.", file=sys.stderr)
    
    input_thread = threading.Thread(target=read_commands, daemon=True)
    input_thread.start()
    print("PsychoPy Display Manager: Input thread scheduled to start.", file=sys.stderr)

    try:
        while keep_running:
            # Process commands from the queue in the main thread
            try:
                command_to_process = command_queue.get_nowait() # Non-blocking get
                # print(f"PDM MainLoop: Processing command from queue: {command_to_process}", file=sys.stderr) # Verbose log
                handle_command(command_to_process) # Process command directly in main thread
            except queue.Empty: # Expected if no commands are pending
                pass
            except Exception as e_queue_proc:
                logger.error(f"PDM MainLoop: Error processing command from queue: {e_queue_proc}")
                traceback.print_exc(file=sys.stderr)
                # Potentially signal shutdown or try to recover, for now just log

            # Apply any pending E/I display updates
            if ei_display_active:
                try:
                    while True:
                        msg_type, val = ei_msg_queue.get_nowait()
                        if msg_type == 'status' and ei_status:
                            ei_status.text = val
                        elif msg_type == 'circle_size' and ei_circle:
                            ei_circle.size = (val, val)
                except queue.Empty:
                    pass

                # Allow experimenter to stop E/I task with ESC key
                keys = event.getKeys(keyList=['escape'])
                if 'escape' in keys:
                    logger.info("Escape pressed – stopping E/I display task.")
                    _stop_ei_display_task()
                    clear_screen()
                    command_queue.put({"action": "show_standby"})

            # Drawing is handled by autoDraw stimuli or by specific command handlers
            try:
                win.flip() 
            except Exception as e:
                print(f"CRITICAL: Error flipping window in main_loop: {e}", file=sys.stderr)
                traceback.print_exc(file=sys.stderr)
                keep_running = False # If flip fails, better to stop
                break
            core.wait(0.01) # Yield time

    except Exception as e:
        print(f"CRITICAL ERROR in PsychoPy Display Manager main_loop: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
    finally:
        print(f"PsychoPy Display Manager: Main loop ended (keep_running={keep_running}). Cleaning up.", file=sys.stderr)
        keep_running = False # Explicitly ensure shutdown signal for other parts like input_thread

        if input_thread and input_thread.is_alive():
            print("PsychoPy Display Manager: Waiting for input thread to finish...", file=sys.stderr)
            # Closing stdin from menu.py should make it stop; give it a moment
            input_thread.join(timeout=0.5) 
            if input_thread.is_alive():
                print("PsychoPy Display Manager: Input thread still alive after join.", file=sys.stderr)
        
        if win and not getattr(win, '_isClosed', True): # Check internal flag if exists, otherwise assume open if win object exists
            try:
                print("PsychoPy Display Manager: Closing window in finally block.", file=sys.stderr)
                win.close()
            except Exception as e_close:
                print(f"PsychoPy Display Manager: Error closing window in finally block: {e_close}", file=sys.stderr)
        
        # core.quit() can be problematic if other psychopy things are running or if not main thread.
        # For a subprocess that is meant to be managed, process termination by menu.py is the final cleanup.
        print("PsychoPy Display Manager: Cleanup finished. Exiting.", file=sys.stderr)

# --------------------
# Helper functions for E/I display management
# --------------------

def _start_ei_display_task(config):
    """Create stimuli in the main thread and launch the background TCP listener."""
    global ei_display_active, ei_msg_queue, ei_circle, ei_status, ei_network_thread, ei_stop_event

    if ei_display_active:
        logger.warning("E/I display already active – start request ignored.")
        return

    # Create stimuli in the main (OpenGL) thread
    try:
        ei_circle = visual.Circle(
            win,
            size=config.get('initial_radius_pix', 50) * 2,
            fillColor=config.get('circle_fill_color', 'cyan'),
            lineColor=config.get('circle_line_color', 'white'),
            units='pix', pos=(0, 0)
        )
        ei_circle.setAutoDraw(True)

        ei_status = visual.TextStim(
            win,
            text="E/I: Waiting for client...",
            pos=(0, win.size[1] * 0.4),
            color=config.get('text_color', 'white'),
            height=config.get('text_height_pix', 20),
            units='pix'
        )
        ei_status.setAutoDraw(True)
    except Exception as stim_err:
        logger.error(f"Failed to create E/I display stimuli: {stim_err}")
        traceback.print_exc(file=sys.stderr)
        return

    # Prepare control objects
    ei_msg_queue = queue.Queue()
    ei_stop_event = threading.Event()

    HOST = config.get('network_ip', '127.0.0.1')
    PORT = config.get('network_port', 5005)
    data_timeout_seconds = config.get('data_timeout_seconds', 10)

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
            ei_msg_queue.put(("status", f"E/I: Waiting for client on {HOST}:{PORT}"))
            while not ei_stop_event.is_set():
                if not client_conn:
                    try:
                        client_conn, addr = server_socket.accept()
                        client_conn.settimeout(0.1)
                        logger.info(f"[E/I] Client connected from {addr}")
                        ei_msg_queue.put(("status", f"E/I: Client connected from {addr[0]}"))
                        last_data_time = time.time()
                    except socket.timeout:
                        continue
                else:
                    try:
                        data_bytes = client_conn.recv(1024)
                        if not data_bytes:
                            logger.info("[E/I] Client disconnected.")
                            ei_msg_queue.put(("status", "E/I: Client disconnected. Waiting..."))
                            client_conn.close()
                            client_conn = None
                            continue
                        last_data_time = time.time()
                        try:
                            ei_ratio = float(data_bytes.decode().strip())
                            new_diameter = max(10, int(ei_ratio * 20))
                            ei_msg_queue.put(("circle_size", new_diameter))
                            ei_msg_queue.put(("status", f"E/I Ratio: {ei_ratio:.2f}"))
                        except Exception:
                            logger.warning(f"[E/I] Invalid data received: {data_bytes}")
                    except socket.timeout:
                        if time.time() - last_data_time > data_timeout_seconds:
                            logger.info("[E/I] Data timeout. Closing client.")
                            ei_msg_queue.put(("status", "E/I: Client timed out. Waiting..."))
                            client_conn.close()
                            client_conn = None
                        continue
                    except Exception as net_err:
                        logger.error(f"[E/I] Network error: {net_err}")
                        ei_msg_queue.put(("status", "E/I: Network error. Waiting..."))
                        if client_conn:
                            client_conn.close()
                        client_conn = None
                        continue
        except Exception as sock_err:
            logger.error(f"[E/I] Server error: {sock_err}")
            ei_msg_queue.put(("status", f"E/I: Server error: {sock_err}"))
        finally:
            if client_conn:
                try:
                    client_conn.close()
                except Exception:
                    pass
            if server_socket:
                try:
                    server_socket.close()
                except Exception:
                    pass
            logger.info("[E/I] Network thread finished.")

    ei_network_thread = threading.Thread(target=network_loop, daemon=True)
    ei_network_thread.start()

    ei_display_active = True
    logger.info("E/I display task started (network thread launched).")


def _stop_ei_display_task():
    """Signal the network thread to stop and remove stimuli."""
    global ei_display_active, ei_msg_queue, ei_circle, ei_status, ei_network_thread, ei_stop_event

    if not ei_display_active:
        logger.info("E/I display not active – stop request ignored.")
        return

    if ei_stop_event:
        ei_stop_event.set()

    if ei_network_thread and ei_network_thread.is_alive():
        ei_network_thread.join(timeout=1.0)

    if ei_circle:
        ei_circle.setAutoDraw(False)
    if ei_status:
        ei_status.setAutoDraw(False)

    # Drain any remaining messages
    while not ei_msg_queue.empty():
        try:
            ei_msg_queue.get_nowait()
        except queue.Empty:
            break

    ei_circle = None
    ei_status = None
    ei_network_thread = None
    ei_stop_event = None
    ei_display_active = False

    logger.info("E/I display task stopped and cleaned up.")

if __name__ == "__main__":
    print("PsychoPy Display Manager: Script starting (__main__).", file=sys.stderr)
    main_loop()
    print("PsychoPy Display Manager: Script execution finished (__main__).", file=sys.stderr) 