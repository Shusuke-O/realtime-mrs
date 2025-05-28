"""
Base task class for the realtime-mrs package.

Provides a common interface and functionality for all experimental tasks.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union
from pathlib import Path
import time
from datetime import datetime

from ..core.logger import get_logger
from ..core.utils import ensure_data_dir, timestamp_string, safe_filename

logger = get_logger(__name__)

@dataclass
class TaskConfig:
    """Configuration for a task."""
    
    # Basic task parameters
    task_name: str = "BaseTask"
    participant_id: str = "default_participant"
    session_id: str = "session_001"
    run_id: Optional[str] = None
    
    # Timing parameters
    max_duration: Optional[float] = None  # Maximum task duration in seconds
    trial_timeout: float = 5.0  # Timeout for individual trials
    
    # Data recording
    data_dir: Optional[Union[str, Path]] = None
    auto_save: bool = True
    save_format: str = "csv"  # csv, json, pickle
    
    # Display parameters
    window_size: List[int] = field(default_factory=lambda: [800, 600])
    fullscreen: bool = False
    background_color: str = "black"
    text_color: str = "white"
    
    # Task-specific parameters (to be extended by subclasses)
    task_params: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Post-initialization processing."""
        if self.run_id is None:
            self.run_id = timestamp_string()
        
        if self.data_dir is None:
            self.data_dir = Path.cwd() / "data"
        else:
            self.data_dir = Path(self.data_dir)

@dataclass
class TaskResult:
    """Result of a task execution."""
    
    # Basic information
    task_name: str
    participant_id: str
    session_id: str
    run_id: str
    
    # Timing information
    start_time: datetime
    end_time: datetime
    duration: float
    
    # Task completion status
    completed: bool = False
    aborted: bool = False
    error: Optional[str] = None
    
    # Task-specific data
    trial_data: List[Dict[str, Any]] = field(default_factory=list)
    summary_data: Dict[str, Any] = field(default_factory=dict)
    
    # File paths
    data_files: List[Path] = field(default_factory=list)
    
    def add_trial(self, trial_data: Dict[str, Any]):
        """Add trial data to the result."""
        self.trial_data.append(trial_data)
    
    def set_summary(self, summary_data: Dict[str, Any]):
        """Set summary data for the task."""
        self.summary_data = summary_data
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary."""
        return {
            'task_name': self.task_name,
            'participant_id': self.participant_id,
            'session_id': self.session_id,
            'run_id': self.run_id,
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat(),
            'duration': self.duration,
            'completed': self.completed,
            'aborted': self.aborted,
            'error': self.error,
            'trial_data': self.trial_data,
            'summary_data': self.summary_data,
            'data_files': [str(f) for f in self.data_files],
        }

class BaseTask(ABC):
    """
    Abstract base class for all experimental tasks.
    
    Provides common functionality for task execution, data recording,
    and result management.
    """
    
    def __init__(self, config: TaskConfig):
        """
        Initialize the task.
        
        Args:
            config: Task configuration
        """
        self.config = config
        self.logger = get_logger(f"{__name__}.{self.__class__.__name__}")
        
        # Task state
        self._is_running = False
        self._is_paused = False
        self._should_abort = False
        self._start_time = None
        self._end_time = None
        
        # Data recording
        self._trial_data = []
        self._current_trial = 0
        
        # Ensure data directory exists
        self.data_dir = ensure_data_dir(self.config.data_dir)
        
        self.logger.info(f"Initialized {self.__class__.__name__} with config: {self.config.task_name}")
    
    @abstractmethod
    def setup(self, **kwargs) -> bool:
        """
        Setup the task (e.g., initialize stimuli, load resources).
        
        Returns:
            True if setup successful, False otherwise
        """
        pass
    
    @abstractmethod
    def run_trial(self, trial_number: int, **kwargs) -> Dict[str, Any]:
        """
        Run a single trial of the task.
        
        Args:
            trial_number: Current trial number (0-indexed)
            **kwargs: Additional trial parameters
            
        Returns:
            Dictionary containing trial data
        """
        pass
    
    @abstractmethod
    def cleanup(self) -> bool:
        """
        Cleanup after task completion (e.g., close files, release resources).
        
        Returns:
            True if cleanup successful, False otherwise
        """
        pass
    
    def get_trial_count(self) -> int:
        """
        Get the total number of trials for this task.
        
        Returns:
            Number of trials
        """
        return self.config.task_params.get('n_trials', 1)
    
    def should_continue(self) -> bool:
        """
        Check if the task should continue running.
        
        Returns:
            True if task should continue, False otherwise
        """
        if self._should_abort:
            return False
        
        # Check maximum duration
        if self.config.max_duration and self._start_time:
            elapsed = time.time() - self._start_time
            if elapsed >= self.config.max_duration:
                self.logger.info(f"Task duration limit reached: {elapsed:.1f}s")
                return False
        
        # Check trial count
        if self._current_trial >= self.get_trial_count():
            return False
        
        return True
    
    def pause(self):
        """Pause the task."""
        self._is_paused = True
        self.logger.info("Task paused")
    
    def resume(self):
        """Resume the task."""
        self._is_paused = False
        self.logger.info("Task resumed")
    
    def abort(self):
        """Abort the task."""
        self._should_abort = True
        self.logger.info("Task abort requested")
    
    def is_running(self) -> bool:
        """Check if task is currently running."""
        return self._is_running
    
    def is_paused(self) -> bool:
        """Check if task is currently paused."""
        return self._is_paused
    
    def add_trial_data(self, trial_data: Dict[str, Any]):
        """
        Add data from a completed trial.
        
        Args:
            trial_data: Dictionary containing trial data
        """
        trial_data['trial_number'] = self._current_trial
        trial_data['timestamp'] = datetime.now().isoformat()
        self._trial_data.append(trial_data)
        
        if self.config.auto_save:
            self._save_trial_data(trial_data)
    
    def _save_trial_data(self, trial_data: Dict[str, Any]):
        """Save trial data to file."""
        try:
            filename = self._get_data_filename()
            
            if self.config.save_format.lower() == 'csv':
                self._save_csv_data(filename, trial_data)
            elif self.config.save_format.lower() == 'json':
                self._save_json_data(filename, trial_data)
            else:
                self.logger.warning(f"Unsupported save format: {self.config.save_format}")
                
        except Exception as e:
            self.logger.error(f"Failed to save trial data: {e}")
    
    def _get_data_filename(self) -> Path:
        """Generate data filename."""
        safe_task_name = safe_filename(self.config.task_name.lower())
        safe_participant = safe_filename(self.config.participant_id)
        safe_session = safe_filename(self.config.session_id)
        safe_run = safe_filename(self.config.run_id)
        
        filename = f"{safe_task_name}_{safe_participant}_{safe_session}_{safe_run}.{self.config.save_format}"
        return self.data_dir / filename
    
    def _save_csv_data(self, filename: Path, trial_data: Dict[str, Any]):
        """Save trial data to CSV file."""
        import csv
        
        file_exists = filename.exists()
        
        with open(filename, 'a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=trial_data.keys())
            
            if not file_exists:
                writer.writeheader()
            
            writer.writerow(trial_data)
    
    def _save_json_data(self, filename: Path, trial_data: Dict[str, Any]):
        """Save trial data to JSON file."""
        import json
        
        # Load existing data if file exists
        if filename.exists():
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            except:
                data = []
        else:
            data = []
        
        # Append new trial data
        data.append(trial_data)
        
        # Save back to file
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def run(self, **kwargs) -> TaskResult:
        """
        Run the complete task.
        
        Args:
            **kwargs: Additional parameters passed to setup and run_trial
            
        Returns:
            TaskResult object containing task results
        """
        self.logger.info(f"Starting task: {self.config.task_name}")
        
        # Initialize result object
        result = TaskResult(
            task_name=self.config.task_name,
            participant_id=self.config.participant_id,
            session_id=self.config.session_id,
            run_id=self.config.run_id,
            start_time=datetime.now(),
            end_time=datetime.now(),  # Will be updated at the end
            duration=0.0,
        )
        
        try:
            # Setup
            self._is_running = True
            self._start_time = time.time()
            
            if not self.setup(**kwargs):
                raise RuntimeError("Task setup failed")
            
            # Run trials
            self._current_trial = 0
            while self.should_continue():
                if self._is_paused:
                    time.sleep(0.1)
                    continue
                
                try:
                    trial_data = self.run_trial(self._current_trial, **kwargs)
                    self.add_trial_data(trial_data)
                    self._current_trial += 1
                    
                except Exception as e:
                    self.logger.error(f"Error in trial {self._current_trial}: {e}")
                    result.error = str(e)
                    break
            
            # Determine completion status
            if self._should_abort:
                result.aborted = True
                self.logger.info("Task was aborted")
            elif self._current_trial >= self.get_trial_count():
                result.completed = True
                self.logger.info("Task completed successfully")
            else:
                self.logger.info("Task ended early")
            
        except Exception as e:
            self.logger.error(f"Task execution failed: {e}")
            result.error = str(e)
            
        finally:
            # Cleanup
            self._end_time = time.time()
            self._is_running = False
            
            try:
                self.cleanup()
            except Exception as e:
                self.logger.error(f"Cleanup failed: {e}")
            
            # Finalize result
            result.end_time = datetime.now()
            result.duration = self._end_time - self._start_time
            result.trial_data = self._trial_data.copy()
            
            # Add data file path
            if self._trial_data:
                result.data_files.append(self._get_data_filename())
            
            self.logger.info(f"Task finished. Duration: {result.duration:.1f}s, Trials: {len(result.trial_data)}")
        
        return result
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get current task status.
        
        Returns:
            Dictionary containing task status information
        """
        elapsed = 0.0
        if self._start_time:
            elapsed = time.time() - self._start_time
        
        return {
            'task_name': self.config.task_name,
            'is_running': self._is_running,
            'is_paused': self._is_paused,
            'should_abort': self._should_abort,
            'current_trial': self._current_trial,
            'total_trials': self.get_trial_count(),
            'elapsed_time': elapsed,
            'max_duration': self.config.max_duration,
        } 