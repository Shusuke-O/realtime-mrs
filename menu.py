#!/usr/bin/env python3
"""
Menu system for the realtime-mrs application.
Provides task selection and configuration options.
"""
import os
import subprocess
import time
import sys
import signal
import threading
import traceback # For error handling
import json # Added for communication with psychopy_manager
from logger import get_logger # Import the logger
from task_introductions import TASK_INTRODUCTIONS # Import task introductions

logger = get_logger("TaskMenu") # Initialize logger for the menu system

class TaskMenu:
    def __init__(self):
        self.tasks = [
            {
                "name": "E/I Ratio Visualization",
                "description": "Visualize E/I ratio with a circle that changes size",
                "command": self.run_ei_visualization
            },
            {
                "name": "M1 Task",
                "description": "M1 tapping task with configurable sequence and repetitions",
                "command": self.run_m1_task
            },
            {
                "name": "V1 Task",
                "description": "V1 orientation discrimination task",
                "command": self.run_v1_task
            },
            {
                "name": "Exit",
                "description": "Exit the application",
                "command": self.exit_program
            }
        ]
        self.psychopy_process = None # Added to manage the psychopy display process
        
    def clear_screen(self):
        """Clear the terminal screen."""
        os.system('cls' if os.name == 'nt' else 'clear')
        
    def display_header(self):
        """Display the application header."""
        self.clear_screen()
        logger.info("Displaying menu header.")
        print("=" * 60)
        print("           REALTIME MRS VISUALIZATION SYSTEM           ")
        print("=" * 60)
        print()
        
    def display_menu(self):
        """Display the main menu."""
        self.display_header()
        print("Available Tasks:")
        print()
        
        for i, task in enumerate(self.tasks, 1):
            print(f"  {i}. {task['name']}")
            print(f"     {task['description']}")
            print()
            
        print("Enter the number of the task you want to run.")
        
    def get_user_choice(self):
        """Get the user's menu choice."""
        while True:
            try:
                choice = int(input("Choice: "))
                if 1 <= choice <= len(self.tasks):
                    return choice
                else:
                    logger.warning(f"Invalid choice: {choice}. Please enter a number between 1 and {len(self.tasks)}.")
            except ValueError:
                logger.warning("Invalid input. Please enter a valid number.")
                
    def get_run_time(self):
        """Get the desired run time in seconds."""
        while True:
            try:
                run_time_str = input("Enter run time in seconds (or press Enter for unlimited): ")
                if run_time_str == "":
                    return None
                run_time = int(run_time_str)
                if run_time > 0:
                    return run_time
                else:
                    logger.warning("Run time must be a positive number.")
            except ValueError:
                logger.warning("Invalid input for run time. Please enter a valid number.")

    def monitor_process(self, process, process_name):
        """Monitor a process and print its output."""
        logger.info(f"Monitoring output for {process_name}...")
        pipe = None
        if "stdout" in process_name:
            pipe = process.stdout
        elif "stderr" in process_name:
            pipe = process.stderr

        if pipe:
            try:
                for line in iter(pipe.readline, ''):
                    logger.info(f"{process_name}: {line.strip()}")
            except Exception as e:
                logger.error(f"Error while monitoring {process_name}: {e}")
            finally:
                # Don't close the pipe here, it belongs to the subprocess Popen object
                # and should be managed by its lifecycle or when Popen object is cleaned up.
                # pipe.close() # REMOVED
                pass 
        logger.info(f"Finished monitoring {process_name}.") # This means readline returned empty, i.e., pipe closed by the other end or EOF

    def run_task_subprocess(self, task_name, command_list, intro_key):
        intro_text = TASK_INTRODUCTIONS.get(intro_key, "No introduction available for this task.")
        self.show_task_intro(task_name, intro_text)
        process = None
        monitor_thread = None
        try:
            logger.info(f"Executing command: {' '.join(command_list)}")
            process = subprocess.Popen(
                command_list,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, # Redirect stderr to stdout
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            monitor_thread = threading.Thread(
                target=self.monitor_process, 
                args=(process, task_name),
                daemon=True
            )
            monitor_thread.start()
            process.wait() # Wait for the subprocess to complete
            logger.info(f"{task_name} process finished with exit code {process.returncode}.")
        except FileNotFoundError:
            logger.error(f"Error: Command not found for {task_name}. Is Poetry installed and in PATH? Command: {' '.join(command_list)}")
        except Exception as e:
            logger.error(f"Error running {task_name}: {e}")
            traceback.print_exc()
        finally:
            if monitor_thread and monitor_thread.is_alive():
                logger.info(f"Waiting for {task_name} monitor thread to finish...")
                monitor_thread.join(timeout=1) # Give thread a moment to finish
            if process and process.poll() is None: # If process is still running
                logger.warning(f"{task_name} process did not terminate as expected. Attempting to terminate.")
                try:
                    process.terminate()
                    process.wait(timeout=2)
                    if process.poll() is None:
                        process.kill()
                except Exception as kill_e:
                    logger.error(f"Error trying to kill {task_name} process: {kill_e}")
        logger.info(f"Task \"{task_name}\" completed. Returning to menu in 2 seconds...")
        time.sleep(2)

    def send_psychopy_command(self, command):
        """Sends a JSON command to the psychopy_display_manager."""
        if self.psychopy_process and self.psychopy_process.stdin and not self.psychopy_process.stdin.closed:
            try:
                pid = self.psychopy_process.pid
                # logger.debug(f"Attempting to send command to PsychoPy (PID: {pid}): {command}") # DEBUG level
                self.psychopy_process.stdin.write(json.dumps(command) + '\n')
                self.psychopy_process.stdin.flush()
                logger.info(f"Sent command to PsychoPy (PID: {pid}): {command}")
            except (BrokenPipeError, OSError) as e: 
                logger.error(f"Error sending command to PsychoPy (PID: {self.psychopy_process.pid if self.psychopy_process else 'unknown'}) (BrokenPipe/OS Error): {e}. PsychoPy process might have crashed or stdin closed.")
                if self.psychopy_process and self.psychopy_process.poll() is None: 
                     logger.info(f"PsychoPy process (PID: {self.psychopy_process.pid}) still polling as alive, but stdin broken. Will attempt restart on next menu loop.")
                self.psychopy_process = None # Mark as None to trigger restart logic in main loop
            except Exception as e:
                logger.error(f"Generic error sending command to PsychoPy (PID: {self.psychopy_process.pid if self.psychopy_process else 'unknown'}): {e}")
        else:
            details = []
            if not self.psychopy_process: details.append("process object is None")
            elif not self.psychopy_process.stdin: details.append("stdin object is None")
            elif self.psychopy_process.stdin.closed: details.append("stdin is closed")
            logger.warning(f"PsychoPy process not ready to receive command. Details: {', '.join(details) if details else 'unknown state'}. Command not sent: {command}")
            # If process exists but stdin is closed, it might be a sign the PDM is shutting down or dead.
            if self.psychopy_process and self.psychopy_process.stdin and self.psychopy_process.stdin.closed:
                 if self.psychopy_process.poll() is None: # If it hasn't exited yet
                      logger.warning(f"stdin closed for PsychoPy process (PID: {self.psychopy_process.pid}) but process still running. It might be shutting down.")
                 else:
                      logger.warning(f"stdin closed and PsychoPy process (PID: {self.psychopy_process.pid}) has exited with code {self.psychopy_process.returncode}. Marking for restart.")
                      self.psychopy_process = None # Mark for restart

    def start_psychopy_manager(self):
        """Starts the psychopy_display_manager.py script."""
        if self.psychopy_process is None or self.psychopy_process.poll() is not None:
            try:
                logger.info("Attempting to start PsychoPy Display Manager process...")
                self.psychopy_process = subprocess.Popen(
                    ["poetry", "run", "python", "psychopy_display_manager.py"],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.PIPE, 
                    text=True,
                    bufsize=1,
                    universal_newlines=True
                )
                logger.info(f"PsychoPy Display Manager Popen called. PID: {self.psychopy_process.pid if self.psychopy_process else 'Failed to get PID'}")
                
                # Threads to monitor psychopy_manager's output
                threading.Thread(target=self.monitor_process, args=(self.psychopy_process, f"PsychoPyMgr_stdout_pid{self.psychopy_process.pid}"), daemon=True).start()
                threading.Thread(target=self.monitor_process, args=(self.psychopy_process, f"PsychoPyMgr_stderr_pid{self.psychopy_process.pid}"), daemon=True).start()
                
                logger.info("PsychoPy Display Manager monitor threads started. Waiting a moment for PDM to initialize and show first message...")
                time.sleep(3.0) # Adjusted wait time slightly
                
                if self.psychopy_process.poll() is None:
                    logger.info("PsychoPy Display Manager process appears to be running after init. Sending show_standby.")
                    self.send_psychopy_command({"action": "show_standby"})
                else:
                    logger.error(f"PsychoPy Display Manager process terminated prematurely after startup. Exit code: {self.psychopy_process.returncode}")
                    self.psychopy_process = None # Ensure it's None if failed

            except Exception as e:
                logger.error(f"CRITICAL: Failed to start PsychoPy Display Manager: {e}")
                traceback.print_exc()
                self.psychopy_process = None 
        else:
            logger.info("PsychoPy Display Manager already marked as running.")

    def stop_psychopy_manager(self):
        """Stops the psychopy_display_manager.py script."""
        logger.info("Attempting to stop PsychoPy Display Manager...")
        if self.psychopy_process and self.psychopy_process.poll() is None:
            pid = self.psychopy_process.pid
            logger.info(f"PsychoPy Display Manager (PID: {pid}) is running. Sending 'exit' command.")
            try:
                self.send_psychopy_command({"action": "exit"})
                if self.psychopy_process.stdin and not self.psychopy_process.stdin.closed:
                    logger.info(f"Closing stdin for PsychoPy Display Manager (PID: {pid}).")
                    self.psychopy_process.stdin.close()
                
                logger.info(f"Waiting for PsychoPy Display Manager (PID: {pid}) to terminate...")
                self.psychopy_process.wait(timeout=5) 
                logger.info(f"PsychoPy Display Manager (PID: {pid}) terminated with code: {self.psychopy_process.returncode}.")
            except subprocess.TimeoutExpired:
                logger.warning(f"PsychoPy Display Manager (PID: {pid}) did not terminate in time, killing.")
                self.psychopy_process.kill()
                self.psychopy_process.wait(timeout=2)
                logger.info(f"PsychoPy Display Manager (PID: {pid}) killed.")
            except (BrokenPipeError, OSError) as e:
                logger.error(f"Error during graceful shutdown of PsychoPy Display Manager (PID: {pid}) (Pipe/OS Error): {e}")
                if self.psychopy_process.poll() is None: 
                    logger.warning(f"PsychoPy Display Manager (PID: {pid}) still running after pipe error, attempting to kill.")
                    self.psychopy_process.kill()
                    self.psychopy_process.wait(timeout=2)
            except Exception as e:
                logger.error(f"Generic error during shutdown of PsychoPy Display Manager (PID: {pid}): {e}")
                if self.psychopy_process.poll() is None: 
                    logger.warning(f"PsychoPy Display Manager (PID: {pid}) still running after generic error, attempting to kill.")
                    self.psychopy_process.kill()
                    self.psychopy_process.wait(timeout=2)
            finally:
                self.psychopy_process = None
                logger.info(f"PsychoPy Display Manager process object (formerly PID: {pid if 'pid' in locals() else 'unknown'}) set to None.")
        else:
            logger.info("PsychoPy Display Manager not running or already stopped. No action taken to stop.")

    def run_ei_visualization(self):
        """Run the E/I ratio visualization task."""
        # Ensure PsychoPy manager is in standby before launching a separate task window
        if self.psychopy_process and self.psychopy_process.poll() is None:
            self.send_psychopy_command({"action": "show_text", "content": "Launching E/I Visualization Task...\n(This task will open a new window)", "wait_for_enter": False })
            time.sleep(0.5) # give a moment for message to display

        intro_text = TASK_INTRODUCTIONS.get("ei_visualization", "No introduction available.")
        # self.show_task_intro("E/I Ratio Visualization", intro_text) # This will show instructions on PDM
        # The original EI viz does not use show_task_intro and manages its own window
        # For now, we will just launch it as before, but ensure PDM is on standby or shows a message.

        self.display_header()
        logger.info("Preparing E/I Ratio Visualization Task")
        run_time = self.get_run_time()
        self.display_header()
        logger.info(f"Starting E/I Ratio Visualization... Duration: {'Unlimited' if run_time is None else f'{run_time} seconds'}")
        print()
        print("Press 'q' in the visualization window to quit and return to the menu at any time.")
        print()
        
        visualizer_cmd = ["poetry", "run", "python", "ei_tcp_event_listener.py"]
        if run_time is not None:
            visualizer_cmd.append(str(run_time))
            
        # This task launches its own separate processes and does not use run_task_subprocess
        # We need to be careful about PsychoPy contexts if ei_tcp_event_listener.py also uses PsychoPy
        
        visualizer = None
        sender = None
        try:
            logger.info("Starting visualizer for E/I Task...")
            visualizer = subprocess.Popen(
                visualizer_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            threading.Thread(target=self.monitor_process, args=(visualizer, f"EIViz_pid{visualizer.pid}"), daemon=True).start()
            
            # Simplified wait for server logic for this example integration
            time.sleep(3) # Assuming server starts within this time
            logger.info("Visualizer for E/I task started. Proceeding with sender...")
            
            logger.info("Starting sender for E/I Task...")
            sender = subprocess.Popen(
                ["poetry", "run", "python", "sent_ei.py"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            threading.Thread(target=self.monitor_process, args=(sender, f"EISender_pid{sender.pid}"), daemon=True).start()
            
            logger.info("E/I Task components (visualizer & sender) are running!")
            
            try:
                while True:
                    if visualizer.poll() is not None:
                        logger.info("E/I Visualizer has stopped.")
                        if sender.poll() is None: sender.terminate()
                        break
                    if sender.poll() is not None:
                        logger.info("E/I Sender has stopped.")
                        if visualizer.poll() is None: visualizer.terminate()
                        break
                    time.sleep(0.5)
            except KeyboardInterrupt:
                logger.info("E/I Task interrupted by user. Shutting down components...")
            
        except Exception as e:
            logger.error(f"Error running E/I task: {e}")
            traceback.print_exc()
        finally:
            logger.info("Cleaning up E/I Task processes...")
            if sender and sender.poll() is None:
                try: sender.terminate(); sender.wait(timeout=1) 
                except: pass
                if sender.poll() is None: sender.kill()
            if visualizer and visualizer.poll() is None:
                try: visualizer.terminate(); visualizer.wait(timeout=1)
                except: pass
                if visualizer.poll() is None: visualizer.kill()
                
        logger.info("E/I Task completed. Returning to menu...")
        # No sleep here, will be handled by main loop showing standby on PDM

    def show_task_intro(self, task_name, description=None):
        self.display_header() # Keep terminal header for experimenter
        print(f"Displaying instructions for {task_name} on PsychoPy screen...")
        print("Waiting for participant to press Enter in the PsychoPy window...")
        
        if description:
            self.send_psychopy_command({"action": "show_text", "content": description, "wait_for_enter": True})
        else:
            self.send_psychopy_command({"action": "show_text", "content": f"Preparing: {task_name}", "wait_for_enter": True})
        
        # input() # Removed: Participant presses Enter in PsychoPy window
        logger.info(f"Participant acknowledged instructions for {task_name}.")

    def run_m1_task(self):
        # First, show instructions via PDM and wait for participant's Enter press (handled by PDM)
        intro_text = TASK_INTRODUCTIONS.get("m1_task", "No introduction available for M1 task.")
        self.show_task_intro("M1 Tapping Task", intro_text)

        # Then, tell PDM to run the M1 task logic in its window
        logger.info("Sending command to PsychoPyDisplayManager to run M1 task...")
        self.send_psychopy_command({"action": "run_m1_task"})
        
        # Menu.py now effectively waits for the PDM to finish the task and return to standby.
        # The PDM will show a completion message and then go to standby on its own.
        # The main menu loop in run() will then show the menu again when PDM is in standby.
        logger.info("M1 task execution requested from PsychoPyDisplayManager. Menu will refresh after task completion.")

    def run_v1_task(self):
        self.run_task_subprocess("V1 Orientation Task", ["poetry", "run", "python", "v1_orientation_task.py"], "v1_task")
        
    def exit_program(self):
        """Exit the program."""
        self.display_header()
        logger.info("Exiting application.")
        self.stop_psychopy_manager() # Stop psychopy before exiting
        print("Thank you for using the Realtime MRS Visualization System.")
        print()
        sys.exit(0)
        
    def run(self):
        """Run the menu system."""
        # Setup signal handler for clean exits
        signal.signal(signal.SIGINT, self.handle_ctrl_c)
        # Attempt to start PsychoPy manager once at the beginning
        if not self.psychopy_process or self.psychopy_process.poll() is not None:
            self.start_psychopy_manager()
        
        while True:
            try:
                # Ensure PsychoPy manager is running at the start of each menu loop
                if not self.psychopy_process or self.psychopy_process.poll() is not None:
                    logger.warning("PsychoPy manager is not running. Attempting to start/restart...")
                    self.start_psychopy_manager()
                    if not self.psychopy_process or self.psychopy_process.poll() is not None:
                        logger.error("CRITICAL: Failed to start/restart PsychoPy manager. Visuals will not be available.")
                        # Optionally, you could add a fallback or exit here if PsychoPy is essential
                        # For now, we'll let the menu continue but log the error.
                    else:
                        self.send_psychopy_command({"action": "show_standby"}) # Show standby if (re)started
                else:
                    # If already running, ensure standby screen is shown before menu
                    self.send_psychopy_command({"action": "show_standby"})

                self.display_menu()
                choice = self.get_user_choice()
                logger.info(f"User selected task number: {choice}")
                selected_task = self.tasks[choice - 1]
                
                if selected_task["command"] == self.exit_program:
                    selected_task["command"]() # Calls exit_program, which handles psychopy stop
                else:
                    selected_task["command"]()
                    # After a task (other than exit) finishes, show standby screen
                    if self.psychopy_process and self.psychopy_process.poll() is None:
                         self.send_psychopy_command({"action": "show_standby"})

            except KeyboardInterrupt:
                logger.info("Ctrl+C pressed in menu. Handling exit.")
                self.handle_ctrl_c(None, None) # Call the handler
            except Exception as e:
                logger.error(f"Unhandled error in menu system: {e}")
                traceback.print_exc()
                logger.info("Attempting to return to menu after error...")
                time.sleep(2)

    def handle_ctrl_c(self, sig, frame):
        logger.info("Ctrl+C detected. Exiting cleanly...")
        self.stop_psychopy_manager()
        sys.exit(0)


if __name__ == "__main__":
    try:
        menu = TaskMenu()
        menu.run()
    except SystemExit:
        logger.info("Application exited normally.")
    except Exception as e:
        logger.critical(f"Critical unhandled error at top level of menu.py: {e}")
        traceback.print_exc()
        print("A critical error occurred. Please check the log file.", file=sys.stderr) 