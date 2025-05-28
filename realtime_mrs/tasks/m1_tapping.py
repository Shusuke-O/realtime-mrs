"""
M1 Motor Cortex Tapping Task for the realtime-mrs package.

This module implements a finger tapping task for M1 motor cortex studies.
"""

from typing import Dict, Any
from .base import BaseTask, TaskConfig

class M1TappingTask(BaseTask):
    """
    M1 Motor Cortex Tapping Task.
    
    A finger tapping task that can be used with keyboard or joystick input
    to study motor cortex activity.
    """
    
    def setup(self, **kwargs) -> bool:
        """Setup the M1 tapping task."""
        self.logger.info("Setting up M1 Tapping Task")
        
        # Get task parameters
        self.controller = self.config.task_params.get('controller', 'keyboard')
        self.repetitions = self.config.task_params.get('repetitions', 3)
        self.sequence = self.config.task_params.get('sequence', ['4', '1', '3', '2', '4'])
        self.sequence_display_time = self.config.task_params.get('sequence_display_time', 2)
        self.response_cutoff_time = self.config.task_params.get('response_cutoff_time', 5)
        
        self.logger.info(f"Controller: {self.controller}")
        self.logger.info(f"Repetitions: {self.repetitions}")
        self.logger.info(f"Sequence: {self.sequence}")
        
        return True
    
    def run_trial(self, trial_number: int, **kwargs) -> Dict[str, Any]:
        """Run a single trial of the M1 tapping task."""
        self.logger.info(f"Running M1 trial {trial_number + 1}")
        
        # Simulate trial execution
        import time
        import random
        
        # Simulate sequence display
        time.sleep(self.sequence_display_time)
        
        # Simulate response collection
        response_time = random.uniform(1.0, 4.0)
        time.sleep(min(response_time, self.response_cutoff_time))
        
        # Simulate accuracy (80% chance of correct sequence)
        accuracy = random.random() < 0.8
        
        trial_data = {
            'trial_number': trial_number,
            'sequence': self.sequence,
            'response_time': response_time,
            'accuracy': accuracy,
            'controller': self.controller,
        }
        
        self.logger.info(f"M1 trial {trial_number + 1} completed: {accuracy}")
        
        return trial_data
    
    def cleanup(self) -> bool:
        """Cleanup after the M1 tapping task."""
        self.logger.info("Cleaning up M1 Tapping Task")
        return True
    
    def get_trial_count(self) -> int:
        """Get the number of trials (repetitions) for this task."""
        return self.repetitions 