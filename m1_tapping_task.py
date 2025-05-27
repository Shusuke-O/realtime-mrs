import traceback
from psychopy import visual, core, event, gui, data
import pygame
import random
import csv

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
        response_cutoff_time = m1_config.get('response_cutoff_time', 5) 
        randomize_sequence = m1_config.get('randomize_sequence', False)

        logger_m1task.info(f"M1 Task Params - Controller: {controller_type}, Joystick: {joystick_device_name}, Reps: {repetitions}")
        logger_m1task.info(f"M1 Task Params - Base Sequence: {base_sequence}, Display Time: {sequence_display_time}s, Response Cutoff: {response_cutoff_time}s, Randomize: {randomize_sequence}")

        # Initialize pygame for controller input
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
                        js.init()
                        if joystick_device_name in js.get_name() or joystick_device_name in js.get_guid():
                            joystick = js
                            use_joystick = True
                            logger_m1task.info(f"M1 Task: Joystick selected: {joystick.get_name()}")
                            break
                    if not use_joystick:
                        logger_m1task.warning(f"M1 Task: Specified joystick '{joystick_device_name}' not found. Found {joystick_count} joysticks. Using keyboard.")
                else:
                    joystick = pygame.joystick.Joystick(0)
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
            tap_clock = core.Clock()
            
            logger_m1task.info(f"M1 Task: Displaying sequence for {sequence_display_time}s. Input allowed.")
            sequence_display_timer = core.CountdownTimer(sequence_display_time)
            
            # Phase 1: Display Sequence and Allow Input
            while sequence_display_timer.getTime() > 0:
                if event.getKeys(keyList=['escape']):
                    logger_m1task.info("M1 Task: Escape key pressed. Aborting M1 task.")
                    return

                current_key_pressed = None
                current_timestamp = None
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

                sequence_text.draw()

                if current_key_pressed and len(response_sequence) < len(expected_sequence):
                    response_sequence.append(current_key_pressed)
                    response_times.append(current_timestamp)
                    logger_m1task.info(f"M1 Task (During Seq Display): Input '{current_key_pressed}' at {current_timestamp:.3f}s. Response {len(response_sequence)}/{len(expected_sequence)}.")
                
                win.flip()
                core.wait(0.001)

            logger_m1task.info(f"M1 Task: Sequence display finished. Collected {len(response_sequence)} responses so far.")

            # Phase 2: Additional Response Time (if needed) with Cutoff
            instruction_text = visual.TextStim(win, text='Replicate the sequence now!', color='white', height=30)
            response_phase_timer = core.CountdownTimer(response_cutoff_time)
            logger_m1task.info(f"M1 Task: Post-sequence response phase. Cutoff: {response_cutoff_time}s.")

            while len(response_sequence) < len(expected_sequence) and response_phase_timer.getTime() > 0:
                if event.getKeys(keyList=['escape']):
                    logger_m1task.info("M1 Task: Escape key pressed. Aborting M1 task.")
                    return

                current_key_pressed = None
                current_timestamp = None

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
            core.wait(2)
            
            # Data saving
            try:
                import os
                if not os.path.exists('data'):
                    os.makedirs('data')
                
                filename = 'data/m1_finger_tapping_data.csv' 
                file_exists = os.path.exists(filename)
                with open(filename, 'a', newline='') as data_file:
                    writer = csv.writer(data_file)
                    
                    if not file_exists:
                        writer.writerow(['repetition', 'expected_sequence', 'response_sequence', 'response_times', 'correct', 'timestamp'])
                    
                    import time
                    writer.writerow([
                        rep + 1,
                        '-'.join(expected_sequence),
                        '-'.join(response_sequence),
                        ','.join([f"{rt:.3f}" for rt in response_times]),
                        sequence_correct,
                        time.strftime('%Y-%m-%d %H:%M:%S')
                    ])
                    
                logger_m1task.info(f"M1 Task: Data saved to {filename}")
                
            except Exception as save_error:
                logger_m1task.error(f"M1 Task: Error saving data: {save_error}")

        # Task completion message
        completion_text = visual.TextStim(win, text='M1 Tapping Task Complete!\n\nThank you for participating.', 
                                        color='white', height=40)
        completion_text.draw()
        win.flip()
        core.wait(3)
        
        logger_m1task.info("M1 Tapping Task completed successfully.")
        
    except Exception as e:
        logger_m1task.error(f"Error in M1 tapping task: {e}")
        traceback.print_exc()
        error_text = visual.TextStim(win, text='An error occurred during the task.\n\nPlease inform the experimenter.', 
                                   color='red', height=30)
        error_text.draw()
        win.flip()
        core.wait(3)

# Test mode for standalone execution
if __name__ == '__main__':
    print("Running M1 Tapping Task in standalone test mode...")
    import logging
    test_logger = logging.getLogger("m1_task_test")
    test_logger.addHandler(logging.StreamHandler())
    test_logger.setLevel(logging.INFO)

    test_config = {
        'controller_type': 'keyboard',
        'repetitions': 2,
        'base_sequence': ['1', '2', '3'],
        'sequence_display_time': 3,
        'response_cutoff_time': 5,
        'randomize_sequence': False
    }

    try:
        from psychopy import visual, core
        win = visual.Window(size=(800, 600), fullscr=False, color='black')
        run_m1_experiment(win, test_config, test_logger)
        win.close()
        core.quit()
    except ImportError:
        print("PsychoPy not available for standalone test")
    except Exception as e:
        print(f"Error in standalone test: {e}") 