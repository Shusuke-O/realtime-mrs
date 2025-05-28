"""
V1 Visual Cortex Orientation Task for the realtime-mrs package.

This module implements an orientation discrimination task for V1 visual cortex studies.
"""

from typing import Dict, Any
from .base import BaseTask, TaskConfig

class V1OrientationTask(BaseTask):
    """
    V1 Visual Cortex Orientation Task.
    
    An orientation discrimination task that can be used to study
    visual cortex activity.
    """
    
    def setup(self, **kwargs) -> bool:
        """Setup the V1 orientation task."""
        self.logger.info("Setting up V1 Orientation Task")
        
        # Get task parameters
        self.stimulus_duration = self.config.task_params.get('stimulus_duration', 0.1)
        self.n_trials = self.config.task_params.get('n_trials', 20)
        self.response_cutoff_time = self.config.task_params.get('response_cutoff_time', 3)
        self.orientations = self.config.task_params.get('orientations', [0, 45, 90, 135])
        self.stimulus_size = self.config.task_params.get('stimulus_size', 100)
        
        self.logger.info(f"Stimulus duration: {self.stimulus_duration}s")
        self.logger.info(f"Number of trials: {self.n_trials}")
        self.logger.info(f"Orientations: {self.orientations}")
        
        return True
    
    def run_trial(self, trial_number: int, **kwargs) -> Dict[str, Any]:
        """Run a single trial of the V1 orientation task."""
        self.logger.info(f"Running V1 trial {trial_number + 1}")
        
        # Simulate trial execution
        import time
        import random
        
        # Select random orientation
        orientation = random.choice(self.orientations)
        
        # Simulate stimulus presentation
        time.sleep(self.stimulus_duration)
        
        # Simulate response collection
        response_time = random.uniform(0.5, 2.5)
        time.sleep(min(response_time, self.response_cutoff_time))
        
        # Simulate accuracy (85% chance of correct orientation detection)
        accuracy = random.random() < 0.85
        
        trial_data = {
            'trial_number': trial_number,
            'orientation': orientation,
            'stimulus_duration': self.stimulus_duration,
            'response_time': response_time,
            'accuracy': accuracy,
        }
        
        self.logger.info(f"V1 trial {trial_number + 1} completed: orientation={orientation}°, accuracy={accuracy}")
        
        return trial_data
    
    def cleanup(self) -> bool:
        """Cleanup after the V1 orientation task."""
        self.logger.info("Cleaning up V1 Orientation Task")
        return True
    
    def get_trial_count(self) -> int:
        """Get the number of trials for this task."""
        return self.n_trials 