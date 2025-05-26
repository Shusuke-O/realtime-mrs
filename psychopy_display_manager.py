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

# --- Potentially import task-specific configurations or utilities ---
from config import get_config # Assuming this is your central config loader
from logger import get_logger # Assuming this is your central logger getter

# --- Import task functions ---
from m1_tapping_task import run_m1_experiment
# from v1_orientation_task import run_v1_experiment # We'll add this later

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
current_stim = []
keep_running = True
input_thread = None
command_queue = queue.Queue() # Thread-safe queue for commands

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
    global keep_running, win
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

if __name__ == "__main__":
    print("PsychoPy Display Manager: Script starting (__main__).", file=sys.stderr)
    main_loop()
    print("PsychoPy Display Manager: Script execution finished (__main__).", file=sys.stderr) 