#!/usr/bin/env python3
"""
Simple usage example for the realtime-mrs modular package.

This script demonstrates how to use the package components in a simple experiment.
"""

import time
from pathlib import Path

# Import the modular components
from realtime_mrs.core import get_logger, load_config, ensure_data_dir
from realtime_mrs.tasks import TaskConfig, BaseTask

# Setup logging
logger = get_logger("simple_example")

class SimpleExampleTask(BaseTask):
    """A simple example task that demonstrates the base task functionality."""
    
    def setup(self, **kwargs):
        """Setup the task."""
        self.logger.info("Setting up simple example task")
        
        # You can access configuration here
        self.display_duration = self.config.task_params.get('display_duration', 2.0)
        self.response_timeout = self.config.task_params.get('response_timeout', 3.0)
        
        self.logger.info(f"Display duration: {self.display_duration}s")
        self.logger.info(f"Response timeout: {self.response_timeout}s")
        
        return True
    
    def run_trial(self, trial_number, **kwargs):
        """Run a single trial."""
        self.logger.info(f"Running trial {trial_number + 1}")
        
        # Simulate showing a stimulus
        self.logger.info("Showing stimulus...")
        time.sleep(self.display_duration)
        
        # Simulate collecting a response
        self.logger.info("Waiting for response...")
        start_time = time.time()
        
        # Simulate response time (random between 0.5 and 2.5 seconds)
        import random
        response_time = random.uniform(0.5, 2.5)
        time.sleep(min(response_time, self.response_timeout))
        
        # Simulate response accuracy (80% chance of correct)
        accuracy = random.random() < 0.8
        
        # Return trial data
        trial_data = {
            'trial_number': trial_number,
            'stimulus_duration': self.display_duration,
            'response_time': response_time,
            'accuracy': accuracy,
            'response': 'correct' if accuracy else 'incorrect',
        }
        
        self.logger.info(f"Trial {trial_number + 1} completed: {trial_data['response']} in {response_time:.2f}s")
        
        return trial_data
    
    def cleanup(self):
        """Cleanup after the task."""
        self.logger.info("Cleaning up simple example task")
        return True
    
    def get_trial_count(self):
        """Get the number of trials to run."""
        return self.config.task_params.get('n_trials', 5)

def main():
    """Main function demonstrating package usage."""
    logger.info("Starting simple realtime-mrs example")
    
    # Load configuration (will use defaults if no config file exists)
    config = load_config()
    logger.info("Configuration loaded")
    
    # Ensure data directory exists
    data_dir = ensure_data_dir("example_data")
    logger.info(f"Data directory: {data_dir}")
    
    # Create task configuration
    task_config = TaskConfig(
        task_name="simple_example",
        participant_id="example_participant",
        session_id="example_session",
        data_dir=data_dir,
        auto_save=True,
        save_format="csv",
        task_params={
            'n_trials': 5,
            'display_duration': 1.5,
            'response_timeout': 3.0,
        }
    )
    
    logger.info(f"Task configuration created: {task_config.task_name}")
    
    # Create and run the task
    task = SimpleExampleTask(task_config)
    
    logger.info("Starting task execution...")
    result = task.run()
    
    # Display results
    logger.info("Task execution completed!")
    logger.info(f"Task completed: {result.completed}")
    logger.info(f"Task aborted: {result.aborted}")
    logger.info(f"Duration: {result.duration:.2f} seconds")
    logger.info(f"Number of trials: {len(result.trial_data)}")
    
    if result.error:
        logger.error(f"Task error: {result.error}")
    
    if result.data_files:
        logger.info(f"Data saved to: {result.data_files[0]}")
    
    # Calculate some basic statistics
    if result.trial_data:
        response_times = [trial['response_time'] for trial in result.trial_data]
        accuracies = [trial['accuracy'] for trial in result.trial_data]
        
        avg_response_time = sum(response_times) / len(response_times)
        accuracy_rate = sum(accuracies) / len(accuracies)
        
        logger.info(f"Average response time: {avg_response_time:.2f}s")
        logger.info(f"Accuracy rate: {accuracy_rate:.1%}")
    
    logger.info("Example completed successfully!")

if __name__ == "__main__":
    main() 