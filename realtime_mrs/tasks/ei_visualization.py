"""
E/I Ratio Visualization Task for the realtime-mrs package.

This module implements an E/I ratio visualization task for real-time feedback.
"""

from typing import Dict, Any
from .base import BaseTask, TaskConfig

class EIVisualizationTask(BaseTask):
    """
    E/I Ratio Visualization Task.
    
    A task that visualizes excitatory/inhibitory ratios in real-time
    for neurofeedback applications.
    """
    
    def setup(self, **kwargs) -> bool:
        """Setup the E/I visualization task."""
        self.logger.info("Setting up E/I Visualization Task")
        
        # Get task parameters
        self.duration = self.config.task_params.get('duration', 60.0)  # seconds
        self.update_rate = self.config.task_params.get('update_rate', 30)  # Hz
        self.circle_base_size = self.config.task_params.get('circle_base_size', 100)
        self.circle_max_size = self.config.task_params.get('circle_max_size', 300)
        
        self.logger.info(f"Duration: {self.duration}s")
        self.logger.info(f"Update rate: {self.update_rate} Hz")
        
        return True
    
    def run_trial(self, trial_number: int, **kwargs) -> Dict[str, Any]:
        """Run a single trial of the E/I visualization task."""
        self.logger.info(f"Running E/I visualization trial {trial_number + 1}")
        
        # Simulate real-time visualization
        import time
        import random
        
        start_time = time.time()
        ei_ratios = []
        
        # Simulate real-time E/I ratio updates
        while time.time() - start_time < self.duration:
            # Simulate E/I ratio (between 0.3 and 1.2)
            ei_ratio = random.uniform(0.3, 1.2)
            ei_ratios.append(ei_ratio)
            
            # Simulate update rate
            time.sleep(1.0 / self.update_rate)
        
        # Calculate statistics
        avg_ei_ratio = sum(ei_ratios) / len(ei_ratios) if ei_ratios else 0.5
        
        trial_data = {
            'trial_number': trial_number,
            'duration': self.duration,
            'avg_ei_ratio': avg_ei_ratio,
            'n_updates': len(ei_ratios),
            'update_rate': self.update_rate,
        }
        
        self.logger.info(f"E/I visualization trial {trial_number + 1} completed: avg_ratio={avg_ei_ratio:.3f}")
        
        return trial_data
    
    def cleanup(self) -> bool:
        """Cleanup after the E/I visualization task."""
        self.logger.info("Cleaning up E/I Visualization Task")
        return True
    
    def get_trial_count(self) -> int:
        """Get the number of trials for this task."""
        return self.config.task_params.get('n_trials', 1) 