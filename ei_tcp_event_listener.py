import traceback
try:
    from psychopy import visual, core, event
    import socket
    import sys
    import time
    from config import get_config
    from logger import get_logger

    logger = get_logger("ei_tcp_event_listener")

    def show_task_intro(window, task_name, duration=None):
        """Show an introduction screen for the task."""
        # Clear the window
        window.flip()
        
        # Create text stimuli
        title = visual.TextStim(window, text=task_name, pos=(0, 0.3), color='white', height=0.07)
        
        duration_text = "Duration: Unlimited" if duration is None else f"Duration: {duration} seconds"
        info = visual.TextStim(window, text=duration_text, pos=(0, 0), color='white', height=0.05)
        
        instruction = visual.TextStim(window, 
                                    text="The circle will change size based on the E/I ratio.\nPress 'q' at any time to return to the menu.", 
                                    pos=(0, -0.3), color='white', height=0.04, wrapWidth=1.5)
        
        continue_text = visual.TextStim(window, text="Press any key to begin", pos=(0, -0.7), color='green', height=0.05)
        
        # Draw all stimuli
        title.draw()
        info.draw()
        instruction.draw()
        continue_text.draw()
        window.flip()
        
        # Wait for key press
        event.waitKeys()
        
        # Clear the window again
        window.flip()

    def main():
        # Initialize window and socket to None so we can safely close them in finally block
        win = None
        s = None
        conn = None
        
        try:
            # Check if duration was provided as command line argument
            duration = None
            if len(sys.argv) > 1:
                try:
                    duration = int(sys.argv[1])
                    logger.info(f"Using duration: {duration} seconds")
                except ValueError:
                    logger.warning(f"Invalid duration: {sys.argv[1]}. Using unlimited duration.")
            
            # Set up the window with proper error handling
            try:
                win = visual.Window([800, 600], monitor="testMonitor", units="norm", fullscr=False)
                logger.info("Visualization window created successfully")
            except Exception as e:
                logger.error(f"Error creating visualization window: {e}")
                return 1
            
            # Show task introduction
            show_task_intro(win, "E/I Ratio Visualization", duration)
            
            # Set up the visual circle
            circle = visual.Circle(win, radius=0.1, fillColor='blue', lineColor='white', pos=(0, 0))
            
            # Set up status text
            status_text = visual.TextStim(win, text="Starting up...", pos=(0, 0.8), color='white', height=0.05)
            info_text = visual.TextStim(win, text="Press 'q' to quit and return to menu", pos=(0, -0.8), color='white', height=0.03)
            
            status_text.draw()
            info_text.draw()
            win.flip()
            
            # Set up TCP server with proper error handling
            HOST = get_config('network.ip', '127.0.0.1')
            PORT = get_config('network.port', 5005)
            logger.info(f"Starting TCP server at {HOST}:{PORT}")
            
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                # Allow port reuse
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind((HOST, PORT))
                s.listen()
                # Set socket timeout to allow checking for keys and timer
                s.settimeout(0.1)
                logger.info(f"TCP server started successfully on {HOST}:{PORT}")
            except Exception as e:
                logger.error(f"Error setting up TCP server: {e}")
                if win:
                    error_text = visual.TextStim(win, text=f"ERROR: Could not start server: {e}", 
                                               pos=(0, 0), color='red', height=0.05, wrapWidth=1.5)
                    error_text.draw()
                    win.flip()
                    time.sleep(3)
                return 1
            
            logger.info("Waiting for client connection...")
            
            # Set up timer if duration is specified
            timer = None
            start_time = None
            if duration is not None:
                timer = core.Clock()
                start_time = time.time()
            
            # Update status text
            status_text.text = f"Listening on {HOST}:{PORT}\nWaiting for connection..."
            status_text.draw()
            info_text.draw()
            win.flip()
            
            # Connection acceptance loop with keyboard check
            client_connected = False
            conn = None
            addr = None
            
            try:
                while not client_connected:
                    # Check for quit key
                    keys = event.getKeys()
                    if 'q' in keys or 'escape' in keys:
                        logger.info("Quit requested. Returning to menu.")
                        return 0
                        
                    # Check for timer expiration if set
                    if timer and timer.getTime() >= duration:
                        logger.info(f"Time limit of {duration} seconds reached.")
                        return 0
                        
                    # Try to accept connection
                    try:
                        conn, addr = s.accept()
                        client_connected = True
                        conn.settimeout(0.1)  # Make client socket non-blocking too
                    except socket.timeout:
                        # This is expected due to non-blocking socket
                        pass
                        
                    # Update the window to keep it responsive
                    win.flip()
                    
                logger.info(f'Connected by {addr}')
                
                # Update status text
                status_text.text = f"Connected to client at {addr[0]}:{addr[1]}"
                status_text.draw()
                info_text.draw()
                win.flip()
                
                # Main processing loop
                last_data_time = time.time()
                while True:
                    # Check for quit key
                    keys = event.getKeys()
                    if 'q' in keys or 'escape' in keys:
                        logger.info("Quit requested. Returning to menu.")
                        break
                        
                    # Check for timer expiration if set
                    if timer and timer.getTime() >= duration:
                        logger.info(f"Time limit of {duration} seconds reached.")
                        break
                        
                    # Check if we haven't received data in a while (detect disconnection)
                    if time.time() - last_data_time > 5:  # 5 seconds timeout
                        status_text.text = "Waiting for data... (timeout in 5s)"
                        status_text.draw()
                        circle.draw()
                        info_text.draw()
                        win.flip()
                        
                        if time.time() - last_data_time > 10:  # 10 seconds timeout
                            logger.warning("No data received for 10 seconds. Assuming client disconnected.")
                            break
                        
                    # Try to receive data
                    try:
                        data = conn.recv(1024)
                        if not data:
                            logger.info("Client disconnected.")
                            break
                            
                        # Update the last data time
                        last_data_time = time.time()
                            
                        try:
                            ei_ratio = float(data.decode().strip())
                            
                            # Update text display
                            status_text.text = f"E/I Ratio: {ei_ratio:.3f}"
                            
                            # Update circle size - scale the radius based on E/I ratio
                            circle.radius = ei_ratio / 20.0  # Scale factor can be adjusted
                            
                            # Draw and update screen
                            status_text.draw()
                            circle.draw()
                            info_text.draw()
                            
                            # Show remaining time if duration is set
                            if timer:
                                time_left = duration - timer.getTime()
                                if time_left > 0:
                                    time_text = visual.TextStim(win, 
                                                              text=f"Time remaining: {int(time_left)} seconds", 
                                                              pos=(0, 0.7), 
                                                              color='white', 
                                                              height=0.04)
                                    time_text.draw()
                            
                            win.flip()
                        except ValueError as ve:
                            logger.warning(f"Invalid data received: {data.decode().strip()}")
                            continue
                        
                    except socket.timeout:
                        # This is expected due to non-blocking socket
                        pass
                    except ConnectionResetError:
                        logger.warning("Connection reset by client.")
                        break
                    except Exception as e:
                        logger.error(f"Error receiving data: {e}")
                        break
                        
                    # Small sleep to prevent CPU hogging
                    time.sleep(0.01)
                    
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                traceback.print_exc()
            
        except Exception as e:
            logger.error(f"Unhandled error: {e}")
            traceback.print_exc()
            return 1
        
        finally:
            logger.info("Shutting down...")
            # Clean up resources
            if conn:
                try:
                    conn.close()
                    logger.info("Client connection closed")
                except:
                    pass
                
            if s:
                try:
                    s.close()
                    logger.info("Server socket closed")
                except:
                    pass
                
            if win:
                try:
                    win.close()
                    logger.info("Visualization window closed")
                except:
                    pass
                
            core.quit()
        
        return 0

    if __name__ == "__main__":
        sys.exit(main())
except Exception as e:
    print("An error occurred:")
    traceback.print_exc()
    try:
        from psychopy import visual, core
        win = visual.Window(size=(800, 600), color='black', units='pix')
        error_text = visual.TextStim(win, text=str(e), color='red', height=30)
        error_text.draw()
        win.flip()
        core.wait(3)
        win.close()
    except Exception:
        pass