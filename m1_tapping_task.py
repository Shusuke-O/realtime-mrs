import traceback
from psychopy import visual, core, event, gui, data # gui and data might not be used here anymore
import pygame # Keep for joystick
    import random
import csv # Added missing import
# Config and logger will be passed in or handled by the caller (psychopy_display_manager)
# from config import get_config
# from logger import get_logger

# logger_m1task = get_logger("m1_tapping_task") # Logger will be passed in

def run_m1_experiment(win, m1_config, logger_m1task):
    """
    Runs the M1 tapping task using the provided PsychoPy window and configuration.

    Args:
        win: The active PsychoPy window object.
        m1_config: A dictionary containing M1 task parameters like:
                   controller_type, joystick_device, repetitions, base_sequence,
                   sequence_display_time, randomize_sequence.
        logger_m1task: Logger instance for M1 task specific logging.
    """
    try:
        logger_m1task.info("Starting M1 Tapping Task experiment logic.")
        # Extract config
        controller_type = m1_config.get('controller_type', 'keyboard') 
        joystick_device_name = m1_config.get('joystick_device', "") 
        repetitions = m1_config.get('repetitions', 3)
        base_sequence = m1_config.get('base_sequence', ['4', '1', '3', '2', '4'])
        sequence_display_time = m1_config.get('sequence_display_time', 2)
        # New config for response cutoff time
        response_cutoff_time = m1_config.get('response_cutoff_time', 5) 
        randomize_sequence = m1_config.get('randomize_sequence', False)

        logger_m1task.info(f"M1 Task Params - Controller: {controller_type}, Joystick: {joystick_device_name}, Reps: {repetitions}")
        logger_m1task.info(f"M1 Task Params - Base Sequence: {base_sequence}, Display Time: {sequence_display_time}s, Response Cutoff: {response_cutoff_time}s, Randomize: {randomize_sequence}")

    # Initialize pygame for controller input
        # It's generally safe to call pygame.init() multiple times.
        # Joystick init should also be safe or re-check.
    pygame.init()
    pygame.joystick.init()

    use_joystick = False
        joystick = None
    if controller_type == 'bluetooth_joystick':
        joystick_count = pygame.joystick.get_count()
        if joystick_count > 0:
                if joystick_device_name:
                for i in range(joystick_count):
                    js = pygame.joystick.Joystick(i)
                        js.init() # Initialize each joystick to check its name/GUID
                        if joystick_device_name in js.get_name() or joystick_device_name in js.get_guid():
                        joystick = js
                        use_joystick = True
                            logger_m1task.info(f"M1 Task: Joystick selected: {joystick.get_name()}")
                        break
                    if not use_joystick:
                        logger_m1task.warning(f"M1 Task: Specified joystick '{joystick_device_name}' not found. Found {joystick_count} joysticks. Using keyboard.")
            else:
                    joystick = pygame.joystick.Joystick(0) # Default to first joystick
                joystick.init()
                use_joystick = True
                    logger_m1task.info(f"M1 Task: Default joystick detected: {joystick.get_name()}")
            else:
                logger_m1task.warning("M1 Task: No joystick detected despite bluetooth_joystick config. Using keyboard input.")
        else:
            logger_m1task.info("M1 Task: Controller set to keyboard. Using keyboard input.")

        # Main experiment loop for repetitions
    for rep in range(repetitions):
        expected_sequence = list(base_sequence)
        if randomize_sequence:
            random.shuffle(expected_sequence)
                logger_m1task.info(f"M1 Task: Repetition {rep+1}/{repetitions} - Randomized Sequence: {expected_sequence}")
        else:
                logger_m1task.info(f"M1 Task: Repetition {rep+1}/{repetitions} - Sequence: {expected_sequence}")

            # Display sequence & collect responses simultaneously
        sequence_text = visual.TextStim(win, text='-'.join(expected_sequence), color='white', height=50)
            
            # Prepare for response collection during sequence display and after
        response_sequence = []
        response_times = []
            # tap_clock will measure time from the onset of the sequence display
        tap_clock = core.Clock()
            
            logger_m1task.info(f"M1 Task: Displaying sequence for {sequence_display_time}s. Input allowed.")
            sequence_display_timer = core.CountdownTimer(sequence_display_time)
            
            # --- Phase 1: Display Sequence and Allow Input --- 
            while sequence_display_timer.getTime() > 0:
                if event.getKeys(keyList=['escape']):
                    logger_m1task.info("M1 Task: Escape key pressed. Aborting M1 task.")
                    return

                # Input polling logic (same as before, but now during sequence display)
                current_key_pressed = None
                current_timestamp = None
                if use_joystick and joystick:
                    for event_pygame in pygame.event.get(): 
                        if event_pygame.type == pygame.JOYBUTTONDOWN:
                            if event_pygame.instance_id == joystick.get_id():
                                current_key_pressed = str(event_pygame.button)
                                current_timestamp = tap_clock.getTime() # Relative to sequence onset
                                break 
                else: 
                    keys = event.getKeys(keyList=['1', '2', '3', '4'], timeStamped=tap_clock)
                    if keys:
                        current_key_pressed, current_timestamp = keys[0]

                sequence_text.draw() # Keep sequence visible

                if current_key_pressed and len(response_sequence) < len(expected_sequence):
                    response_sequence.append(current_key_pressed)
                    response_times.append(current_timestamp)
                    logger_m1task.info(f"M1 Task (During Seq Display): Input '{current_key_pressed}' at {current_timestamp:.3f}s. Response {len(response_sequence)}/{len(expected_sequence)}.")
                    # Optional: Brief visual feedback for tap, but might be distracting here.
                    # For now, no extra visual feedback during sequence display phase.
                
                win.flip()
                core.wait(0.001) # Yield time

            logger_m1task.info(f"M1 Task: Sequence display finished. Collected {len(response_sequence)} responses so far.")

            # --- Phase 2: Additional Response Time (if needed) with Cutoff --- 
        instruction_text = visual.TextStim(win, text='Replicate the sequence now!', color='white', height=30)
            # The tap_clock continues from the sequence display onset.
            # Or, reset clock if RT should be from instruction onset: tap_clock.reset() 
            # For now, let's keep tap_clock continuous to measure from sequence start.
            # The response_cutoff_time will apply to the total time allowed since this phase starts.
            
            response_phase_timer = core.CountdownTimer(response_cutoff_time)
            logger_m1task.info(f"M1 Task: Post-sequence response phase. Cutoff: {response_cutoff_time}s.")

            while len(response_sequence) < len(expected_sequence) and response_phase_timer.getTime() > 0:
                if event.getKeys(keyList=['escape']):
                    logger_m1task.info("M1 Task: Escape key pressed. Aborting M1 task.")
                    return

                current_key_pressed = None
                current_timestamp = None # This timestamp will be from tap_clock (sequence onset)

                if use_joystick and joystick:
                for event_pygame in pygame.event.get():
                    if event_pygame.type == pygame.JOYBUTTONDOWN:
                            if event_pygame.instance_id == joystick.get_id():
                                current_key_pressed = str(event_pygame.button)
                                current_timestamp = tap_clock.getTime()
                                break 
            else:
                keys = event.getKeys(keyList=['1', '2', '3', '4'], timeStamped=tap_clock)
                    if keys:
                        current_key_pressed, current_timestamp = keys[0]
                
                instruction_text.draw()

                if current_key_pressed:
                    response_sequence.append(current_key_pressed)
                    response_times.append(current_timestamp)
                    logger_m1task.info(f"M1 Task (Post-Seq Response): Input '{current_key_pressed}' at {current_timestamp:.3f}s. Response {len(response_sequence)}/{len(expected_sequence)}.")
                    
                    tap_feedback_stim = visual.TextStim(win, text=f"Got: {current_key_pressed}", 
                                                      pos=(instruction_text.pos[0], instruction_text.pos[1] - 50), 
                                                      color='cyan', height=25)
                    tap_feedback_stim.draw() 
                    win.flip() 
                    core.wait(0.15) 
                else:
                    win.flip() 
                
                if len(response_sequence) == len(expected_sequence):
                    logger_m1task.info("M1 Task: Full sequence entered.")
                    break
                core.wait(0.001)
            
            if response_phase_timer.getTime() <= 0 and len(response_sequence) < len(expected_sequence):
                logger_m1task.info(f"M1 Task: Response cutoff time ({response_cutoff_time}s) reached. {len(response_sequence)} responses collected.")

            # Evaluate sequence
        sequence_correct = response_sequence == expected_sequence
            feedback_text_str = 'Correct!' if sequence_correct else 'Incorrect sequence.'
            feedback_stim = visual.TextStim(win, text=feedback_text_str, color='green' if sequence_correct else 'red', height=40)
            feedback_stim.draw()
        win.flip()
            core.wait(2) # Display feedback for 2 seconds
            
            # Data saving
            try:
                # Ensure data directory exists (good practice, though menu.py might also do this)
                import os
                if not os.path.exists('data'):
                    os.makedirs('data')
                
                # Use a more unique filename or pass from PDM/menu if needed
                # For now, keep it simple as in original but log clearly
                filename = 'data/m1_finger_tapping_data.csv' 
                file_exists = os.path.exists(filename)
                with open(filename, 'a', newline='') as data_file:
                    writer = csv.writer(data_file)
                    if not file_exists:
                        writer.writerow(['Repetition', 'ExpectedSequence', 'ResponseSequence', 'ResponseTimes', 'Correct'])
                    writer.writerow([rep+1, '-'.join(expected_sequence), '-'.join(response_sequence), '-'.join([f"{rt:.3f}" for rt in response_times]), sequence_correct])
                logger_m1task.info(f"M1 Task: Rep {rep+1} data saved to {filename}. Correct: {sequence_correct}")
            except Exception as e_save:
                logger_m1task.error(f"M1 Task: Error saving data - {e_save}")

        logger_m1task.info("M1 Tapping Task completed successfully.")

except Exception as e:
        logger_m1task.error(f"M1 Task: An error occurred during the M1 task experiment: {e}")
        logger_m1task.error(traceback.format_exc())
        try:
            # Attempt to display error on the provided PsychoPy window
            error_text = visual.TextStim(win, text=f"Error in M1 Task: {str(e)}\nCheck logs.",
                                       color='red', height=0.07, wrapWidth=1.8)
        error_text.draw()
        win.flip()
            core.wait(3) # Show error for 3 seconds
        except Exception as e_display:
            logger_m1task.error(f"M1 Task: Could not display error in M1 task window: {e_display}")
    finally:
        # DO NOT close win or core.quit() here, as it's managed by psychopy_display_manager.py
        # Cleanup specific to M1 task if any (e.g., specific pygame joystick de-init if necessary)
        if pygame.joystick.get_init():
             pygame.joystick.quit()
        if pygame.get_init(): # Quit all pygame modules
             pygame.quit()
        logger_m1task.info("M1 Tapping Task: run_m1_experiment function finished.")

# This block is for testing m1_tapping_task.py in isolation
if __name__ == '__main__':
    print("Running M1 Tapping Task in standalone test mode...")
    # Setup a dummy logger for testing
    import logging
    test_logger = logging.getLogger("m1_task_test")
    test_logger.addHandler(logging.StreamHandler())
    test_logger.setLevel(logging.INFO)

    # Setup a dummy config for testing
    test_m1_config = {
        'controller_type': 'keyboard',  # or 'bluetooth_joystick'
        'joystick_device': "", # Specify joystick name if bluetooth_joystick
        'repetitions': 2,
        'base_sequence': ['1', '2', '3'],
        'sequence_display_time': 1.5,
        'randomize_sequence': True
    }
    test_logger.info(f"Test mode using config: {test_m1_config}")

    # Create a temporary window for testing
    try:
        test_win = visual.Window(size=(800, 600), color='black', units='pix', fullscr=False)
        run_m1_experiment(test_win, test_m1_config, test_logger)
    except Exception as e_test:
        test_logger.error(f"Error in M1 standalone test: {e_test}")
        test_logger.error(traceback.format_exc())
    finally:
        if 'test_win' in locals() and test_win:
            test_win.close()
        core.quit()
        print("M1 Tapping Task standalone test finished.")