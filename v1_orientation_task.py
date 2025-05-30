import traceback
import yaml
from psychopy import visual, core, event, data
import random
import os

def run_v1_experiment(win, v1_config, logger_v1task):
    """
    Runs the V1 orientation task using the provided PsychoPy window and configuration.

    Args:
        win: The active PsychoPy window object.
        v1_config: A dictionary containing V1 task parameters like:
                   stimulus_duration, n_trials, participant_id, session_id.
        logger_v1task: Logger instance for V1 task specific logging.
    """
    try:
        logger_v1task.info("Starting V1 Orientation Task experiment logic.")

        # Extract config
        stimulus_duration = v1_config.get('stimulus_duration', 0.1)
        n_trials = v1_config.get('n_trials', 20)
        participant_id = v1_config.get('participant_id', 'test_participant')
        session_id = v1_config.get('session_id', '001')
        response_cutoff_time = v1_config.get('response_cutoff_time', 3)
        
        logger_v1task.info(f"V1 Task Params - Stimulus Duration: {stimulus_duration}s, N Trials: {n_trials}, Response Cutoff: {response_cutoff_time}s")
        logger_v1task.info(f"V1 Task Params - Participant: {participant_id}, Session: {session_id}")

        # Define the grating stimulus
        grating = visual.GratingStim(win=win, tex='sin', mask='gauss', size=200, sf=0.05, contrast=0.8)
        feedback_stim = visual.TextStim(win=win, text='', color='black', height=30)
        orientations = [-5, 5]  # Degrees from vertical

        # Experiment Setup (Data Handling)
        experiment_info = {'participant': participant_id, 'session': session_id}
        timestamp = data.getDateStr()
        
        # Ensure data directory exists
        data_dir = 'data'
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)
            logger_v1task.info(f"Created data directory: {data_dir}")
        
        filename_base = f"v1_orientation_{experiment_info['participant']}_{experiment_info['session']}_{timestamp}"
        data_file_path = os.path.join(data_dir, filename_base)

        this_exp = data.ExperimentHandler(name='V1Orientation', version='',
                                        extraInfo=experiment_info, runtimeInfo=True,
                                        savePickle=True, saveWideText=True,
                                        dataFileName=data_file_path)
        logger_v1task.info(f"V1 Task: Saving data to files starting with: {data_file_path}")

        # Create a trial handler
        trial_list = []
        for _ in range(n_trials):
            trial_list.append({'orientation': random.choice(orientations)})
        
        trials = data.TrialHandler(nReps=1, method='random', 
                                  trialList=trial_list, 
                                  name='trials')
        this_exp.addLoop(trials)

        # Run Experiment
        logger_v1task.info("V1 Task: Starting trials.")
        for this_trial in trials:
            if event.getKeys(keyList=['escape']):
                logger_v1task.info("V1 Task: Escape key pressed during trial loop. Ending task early.")
                break 

            orientation_val = this_trial['orientation']
            grating.ori = orientation_val
            correct_response = 'left' if orientation_val < 0 else 'right'
        
            # Display grating
            grating.draw()
            win.flip() 
            stimulus_onset_time = core.getTime() 
            core.wait(stimulus_duration) 
            win.flip()  # Clear stimulus
            stimulus_offset_time = core.getTime()

            # Wait for response with timeout
            keys = event.waitKeys(maxWait=response_cutoff_time, keyList=['left', 'right', 'escape'], timeStamped=core.Clock())
        
            participant_response = None
            reaction_time = None
            accuracy = 0  # Default to incorrect/timeout

            if keys is None:  # Timeout
                logger_v1task.info("V1 Task: No response within cutoff time.")
                participant_response = 'timeout'
            elif keys[0][0] == 'escape':
                logger_v1task.info("V1 Task: Escape key pressed waiting for response. Ending task early.")
                break 
            else:
                participant_response, rt_from_stim_offset = keys[0]
                reaction_time = rt_from_stim_offset 
                accuracy = int(participant_response == correct_response)
        
            # Store data
            this_exp.addData('orientation', orientation_val)
            this_exp.addData('participant_response', participant_response)
            this_exp.addData('reaction_time', reaction_time)
            this_exp.addData('accuracy', accuracy)
            this_exp.addData('stimulus_onset', stimulus_onset_time)
            this_exp.addData('stimulus_offset', stimulus_offset_time)
            this_exp.nextEntry() 

            # Display feedback
            feedback_stim.text = 'Correct!' if accuracy else 'Incorrect'
            feedback_stim.color = 'green' if accuracy else 'red'
            feedback_stim.draw()
            win.flip()
            core.wait(1.0)  # Feedback duration
            win.flip()  # Clear feedback before next trial or end
        
            rt_str = f"{reaction_time:.3f}" if reaction_time is not None else "N/A"
            logger_v1task.info(f"V1 Trial {trials.thisN + 1}/{n_trials}: ori={orientation_val}, resp={participant_response}, acc={accuracy}, rt={rt_str}")

        # End of Experiment
        this_exp.saveAsWideText(data_file_path + '.csv', delim=',')
        this_exp.saveAsPickle(data_file_path)
        logger_v1task.info("V1 Orientation Task completed. Data saving routines executed.")

        # Task completion message
        completion_text = visual.TextStim(win, text='V1 Orientation Task Complete!\n\nThank you for participating.', 
                                        color='white', height=40)
        completion_text.draw()
        win.flip()
        core.wait(3)

    except Exception as e:
        logger_v1task.error(f"V1 Task: An error occurred: {e}")
        logger_v1task.error(traceback.format_exc())
        try:
            error_text_stim = visual.TextStim(win, text=f"Error in V1 Task: {str(e)}\nCheck logs.",
                                           color='red', height=30, wrapWidth=800)
            error_text_stim.draw()
            win.flip()
            core.wait(3)
        except Exception as e_display:
            logger_v1task.error(f"V1 Task: Could not display error in V1 task window: {e_display}")
    finally:
        logger_v1task.info("V1 Orientation Task: run_v1_experiment function finished.")

# For standalone testing
if __name__ == '__main__':
    print("Running V1 Orientation Task in standalone test mode...")
    import logging
    test_logger = logging.getLogger("v1_task_test")
    test_logger.addHandler(logging.StreamHandler())
    test_logger.setLevel(logging.INFO)

    # Example config for testing
    test_v1_config = {
        'stimulus_duration': 0.15,
        'n_trials': 5, 
        'participant_id': 'v1_test',
        'session_id': 's01',
        'response_cutoff_time': 2.5
    }
    test_logger.info(f"V1 Test mode using config: {test_v1_config}")

    test_win = None
    try:
        test_win = visual.Window(size=(800, 600), color='gray', units='pix', fullscr=False)
        run_v1_experiment(test_win, test_v1_config, test_logger)
    except Exception as e_test:
        test_logger.error(f"Error in V1 standalone test: {e_test}")
        test_logger.error(traceback.format_exc())
    finally:
        if test_win:
            test_win.close()
        core.quit()
        print("V1 Orientation Task standalone test finished.") 