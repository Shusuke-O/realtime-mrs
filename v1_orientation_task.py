import traceback
import yaml # For loading config

try:
    from psychopy import visual, core, event, data
    import random
    import csv
    from logger import get_logger

    logger = get_logger("v1_orientation_task")

    # Load configuration
    try:
        with open('config.yaml', 'r') as f:
            config = yaml.safe_load(f)
        stimulus_duration = config.get('v1_task', {}).get('stimulus_duration', 0.1)
        logger.info(f"Loaded stimulus duration from config: {stimulus_duration}s")
    except FileNotFoundError:
        logger.warning("config.yaml not found. Using default stimulus duration: 0.1s")
        stimulus_duration = 0.1
    except Exception as e:
        logger.error(f"Error loading config.yaml: {e}. Using default stimulus duration: 0.1s")
        stimulus_duration = 0.1

    # Create a window
    win = visual.Window(size=(800, 600), color='gray', units='pix', fullscr=False) # fullscr=False for easier debugging
    logger.info("V1 Orientation Task started. Window created.")

    # Define the grating stimulus
    grating = visual.GratingStim(win=win, tex='sin', mask='gauss', size=200, sf=0.05, contrast=0.8)
    # fixation = visual.TextStim(win=win, text='+', color='black', height=30) # Fixation cross removed
    feedback = visual.TextStim(win=win, text='', color='black', height=30)
    orientations = [-5, 5]

    # --- Experiment Setup ---
    experiment_info = {'participant': 'test', 'session': '001'}
    timestamp = data.getDateStr()
    filename = f"data/v1_orientation_{experiment_info['participant']}_{experiment_info['session']}_{timestamp}.csv"
    
    # Ensure data directory exists
    import os
    if not os.path.exists('data'):
        os.makedirs('data')
        logger.info("Created data directory.")

    # Data file setup using PsychoPy's data.ExperimentHandler for more robust saving
    this_exp = data.ExperimentHandler(name='V1Orientation', version='',
                                    extraInfo=experiment_info, runtimeInfo=True,
                                    originPath='v1_orientation_task.py',
                                    savePickle=True, saveWideText=True,
                                    dataFileName=filename)
    logger.info(f"Saving data to: {filename}")

    n_trials = 20 # Can also be moved to config.yaml if needed
    logger.info(f"Number of trials: {n_trials}")

    # Create a trial handler
    trial_list = []
    for _ in range(n_trials):
        trial_list.append({'orientation': random.choice(orientations)})
    
    trials = data.TrialHandler(nReps=1, method='random', 
                                trialList=trial_list, 
                                name='trials')
    this_exp.addLoop(trials)

    # --- Run Experiment ---
    for this_trial in trials:
        orientation = this_trial['orientation']
        grating.ori = orientation
        correct_response = 'left' if orientation < 0 else 'right'
        
        # Display grating for configured duration
        grating.draw()
        win.flip() # Show stimulus
        stimulus_onset_time = core.getTime() # Record onset time
        core.wait(stimulus_duration) # Wait for stimulus_duration
        win.flip() # Clear stimulus by flipping to a blank screen (gray background)
        stimulus_offset_time = core.getTime()

        # Wait for response
        keys = event.waitKeys(keyList=['left', 'right', 'escape'], timeStamped=core.Clock())
        
        participant_response = None
        reaction_time = None

        if keys[0][0] == 'escape':
            logger.info("Escape key pressed. Ending task early.")
            break # Exit the loop if escape is pressed

        participant_response, rt_from_stim_offset = keys[0]
        reaction_time = rt_from_stim_offset # RT relative to when stimulus disappeared

        accuracy = int(participant_response == correct_response)
        
        # Store data for this trial
        trials.addData('participant_response', participant_response)
        trials.addData('reaction_time', reaction_time)
        trials.addData('accuracy', accuracy)
        trials.addData('stimulus_onset', stimulus_onset_time)
        trials.addData('stimulus_offset', stimulus_offset_time)
        this_exp.nextEntry() # Advance to the next row in the data file

        # Display feedback
        feedback.text = 'Correct!' if accuracy else 'Incorrect'
        feedback.draw()
        win.flip()
        core.wait(1.0) # Feedback duration
        
        logger.info(f"Trial {trials.thisN + 1}: ori={orientation}, resp={participant_response}, acc={accuracy}, rt={reaction_time:.3f}")

    # --- End of Experiment ---
    # Data saving is handled by ExperimentHandler, but ensure a final flip if needed
    # win.flip() # Optional: clear screen at the very end
    logger.info("V1 Orientation Task completed. Data saved.")

except Exception as e:
    logger.error(f"An error occurred in V1 Orientation Task: {e}")
    logger.exception("Traceback:")
    # Attempt to show error in PsychoPy window only if win is defined
    if 'win' in locals() and win is not None:
        try:
            error_text = visual.TextStim(win, text=f"Error: {str(e)}\nSee app.log for details.", color='red', height=20, wrapWidth=750)
            error_text.draw()
            win.flip()
            core.wait(5)
        except Exception as e_display:
            logger.error(f"Could not display error in PsychoPy window: {e_display}")
finally:
    # Ensure PsychoPy resources are released
    if 'win' in locals() and win is not None:
        win.close()
    core.quit() # Important to allow psychopy to clean up properly
    logger.info("PsychoPy window closed and core quit.")