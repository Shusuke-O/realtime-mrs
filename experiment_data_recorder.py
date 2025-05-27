#!/usr/bin/env python3
"""
Experiment Data Recorder
Centralized data acquisition and recording system using Lab Streaming Layer (LSL).
Records data from all experiment components (FSL-MRS, tasks, events) into synchronized files.
"""

import os
import time
import threading
import json
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, asdict
import numpy as np

try:
    import pylsl
    from pylsl import StreamInfo, StreamOutlet, resolve_stream, StreamInlet
    LSL_AVAILABLE = True
except ImportError:
    print("Warning: pylsl not available. Install with: pip install pylsl")
    LSL_AVAILABLE = False

from config import get_config
from logger import get_logger

logger = get_logger("ExperimentDataRecorder")

@dataclass
class ExperimentSession:
    """Experiment session metadata."""
    participant_id: str
    session_id: str
    experiment_name: str
    start_time: datetime
    end_time: Optional[datetime] = None
    data_directory: str = ""
    recording_files: Dict[str, str] = None
    
    def __post_init__(self):
        if self.recording_files is None:
            self.recording_files = {}

@dataclass
class TaskEvent:
    """Task event for logging experimental events."""
    timestamp: float
    event_type: str  # 'task_start', 'task_end', 'stimulus', 'response', 'intervention'
    task_name: str
    event_data: Dict[str, Any]
    participant_id: str
    session_id: str

class ExperimentDataRecorder:
    """
    Centralized experiment data recorder using LSL.
    
    This class provides:
    1. LSL-based data recording from multiple streams
    2. Event logging and synchronization
    3. Automatic file organization
    4. Real-time data monitoring
    5. Post-experiment data export
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the experiment data recorder.
        
        Args:
            config: Configuration dictionary
        """
        if not LSL_AVAILABLE:
            raise ImportError("LSL is required for data recording. Install with: pip install pylsl")
        
        self.config = config or self._load_default_config()
        self.logger = logger
        
        # Session management
        self.current_session: Optional[ExperimentSession] = None
        self.is_recording = False
        
        # LSL streams
        self.event_outlet: Optional[StreamOutlet] = None
        self.data_inlets: Dict[str, StreamInlet] = {}
        self.recording_threads: Dict[str, threading.Thread] = {}
        
        # Data storage
        self.data_directory = self.config.get('data_directory', 'experiment_data')
        self.auto_save_interval = self.config.get('auto_save_interval', 30.0)  # seconds
        
        # Event tracking
        self.events: List[TaskEvent] = []
        self.event_lock = threading.Lock()
        
        # Control
        self.stop_event = threading.Event()
        
        self.logger.info("Experiment Data Recorder initialized")
    
    def _load_default_config(self) -> Dict[str, Any]:
        """Load default configuration."""
        try:
            return {
                'data_directory': get_config('experiment_recording.data_directory', 'experiment_data'),
                'auto_save_interval': get_config('experiment_recording.auto_save_interval', 30.0),
                'streams_to_record': get_config('experiment_recording.streams_to_record', [
                    'FSL-MRS-EI-Ratio',
                    'ExperimentEvents',
                    'TaskResponses',
                    'Physiological'
                ]),
                'file_formats': get_config('experiment_recording.file_formats', ['xdf', 'csv']),
                'buffer_length': get_config('experiment_recording.buffer_length', 360),
                'sync_tolerance': get_config('experiment_recording.sync_tolerance', 0.001),
            }
        except Exception as e:
            logger.warning(f"Could not load config, using defaults: {e}")
            return {
                'data_directory': 'experiment_data',
                'auto_save_interval': 30.0,
                'streams_to_record': ['FSL-MRS-EI-Ratio', 'ExperimentEvents'],
                'file_formats': ['xdf', 'csv'],
                'buffer_length': 360,
                'sync_tolerance': 0.001,
            }
    
    def start_session(self, participant_id: str, session_id: str, 
                     experiment_name: str = "realtime_mrs") -> ExperimentSession:
        """
        Start a new experiment session.
        
        Args:
            participant_id: Participant identifier
            session_id: Session identifier
            experiment_name: Name of the experiment
            
        Returns:
            ExperimentSession: The created session
        """
        if self.is_recording:
            raise RuntimeError("Cannot start new session while recording is active")
        
        # Create session
        start_time = datetime.now()
        session = ExperimentSession(
            participant_id=participant_id,
            session_id=session_id,
            experiment_name=experiment_name,
            start_time=start_time
        )
        
        # Create data directory
        timestamp_str = start_time.strftime("%Y%m%d_%H%M%S")
        session_dir = f"{participant_id}_{session_id}_{timestamp_str}"
        session.data_directory = os.path.join(self.data_directory, session_dir)
        os.makedirs(session.data_directory, exist_ok=True)
        
        # Setup LSL event stream
        self._setup_event_stream()
        
        self.current_session = session
        self.logger.info(f"Started experiment session: {participant_id}/{session_id}")
        self.logger.info(f"Data directory: {session.data_directory}")
        
        # Log session start event
        self.log_event('session_start', 'experiment', {
            'participant_id': participant_id,
            'session_id': session_id,
            'experiment_name': experiment_name,
            'start_time': start_time.isoformat(),
            'data_directory': session.data_directory
        })
        
        return session
    
    def _setup_event_stream(self):
        """Setup LSL stream for experiment events."""
        try:
            # Create event stream
            info = StreamInfo(
                name='ExperimentEvents',
                type='Events',
                channel_count=1,
                nominal_srate=0,  # Irregular sampling
                channel_format=pylsl.cf_string,
                source_id='experiment-events-001'
            )
            
            # Add metadata
            desc = info.desc()
            desc.append_child_value("manufacturer", "RealtimeMRS")
            desc.append_child_value("unit", "event")
            desc.append_child_value("description", "Experiment events and markers")
            
            # Add channel information
            channels = desc.append_child("channels")
            ch = channels.append_child("channel")
            ch.append_child_value("label", "Event")
            ch.append_child_value("unit", "string")
            ch.append_child_value("type", "Event")
            
            self.event_outlet = StreamOutlet(info)
            self.logger.info("LSL event stream created successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to setup event stream: {e}")
            raise
    
    def start_recording(self) -> bool:
        """
        Start recording data from all available LSL streams.
        
        Returns:
            bool: True if recording started successfully
        """
        if not self.current_session:
            raise RuntimeError("No active session. Call start_session() first.")
        
        if self.is_recording:
            self.logger.warning("Recording already active")
            return True
        
        try:
            # Discover available streams
            available_streams = self._discover_streams()
            
            if not available_streams:
                self.logger.warning("No LSL streams found to record")
                return False
            
            # Start recording threads for each stream
            self.stop_event.clear()
            
            for stream_name, stream_info in available_streams.items():
                self._start_stream_recording(stream_name, stream_info)
            
            self.is_recording = True
            self.logger.info(f"Started recording {len(available_streams)} streams")
            
            # Log recording start event
            self.log_event('recording_start', 'system', {
                'streams': list(available_streams.keys()),
                'session_directory': self.current_session.data_directory
            })
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start recording: {e}")
            return False
    
    def _discover_streams(self) -> Dict[str, Any]:
        """Discover available LSL streams."""
        try:
            self.logger.info("Discovering LSL streams...")
            # Try with timeout parameter first, fall back to no timeout
            try:
                streams = resolve_stream(timeout=2.0)
            except TypeError:
                # Older pylsl versions don't support timeout parameter
                streams = resolve_stream()
            
            available_streams = {}
            streams_to_record = self.config.get('streams_to_record', [])
            
            for stream in streams:
                stream_name = stream.name()
                
                # Record all streams if no specific list provided, or if stream is in the list
                if not streams_to_record or stream_name in streams_to_record:
                    available_streams[stream_name] = stream
                    self.logger.info(f"Found stream to record: {stream_name} "
                                   f"(type: {stream.type()}, channels: {stream.channel_count()})")
            
            return available_streams
            
        except Exception as e:
            self.logger.error(f"Error discovering streams: {e}")
            return {}
    
    def _start_stream_recording(self, stream_name: str, stream_info: Any):
        """Start recording a specific stream."""
        try:
            # Create inlet
            inlet = StreamInlet(stream_info, max_chunklen=0)
            self.data_inlets[stream_name] = inlet
            
            # Create recording thread
            thread = threading.Thread(
                target=self._record_stream_data,
                args=(stream_name, inlet),
                daemon=True
            )
            thread.start()
            self.recording_threads[stream_name] = thread
            
            self.logger.info(f"Started recording thread for stream: {stream_name}")
            
        except Exception as e:
            self.logger.error(f"Failed to start recording for stream {stream_name}: {e}")
    
    def _record_stream_data(self, stream_name: str, inlet: StreamInlet):
        """Record data from a specific stream."""
        data_buffer = []
        timestamps_buffer = []
        
        # Create output file
        output_file = os.path.join(
            self.current_session.data_directory,
            f"{stream_name}_{self.current_session.start_time.strftime('%Y%m%d_%H%M%S')}.csv"
        )
        
        self.current_session.recording_files[stream_name] = output_file
        
        try:
            with open(output_file, 'w') as f:
                # Write header
                f.write("timestamp,data\n")
                
                last_save_time = time.time()
                
                while not self.stop_event.is_set():
                    # Pull data
                    samples, timestamps = inlet.pull_chunk(timeout=1.0)
                    
                    if samples:
                        for sample, timestamp in zip(samples, timestamps):
                            data_buffer.append(sample)
                            timestamps_buffer.append(timestamp)
                            
                            # Write to file immediately for real-time access
                            if isinstance(sample, list):
                                data_str = ','.join(map(str, sample))
                            else:
                                data_str = str(sample)
                            
                            f.write(f"{timestamp},{data_str}\n")
                    
                    # Periodic flush
                    current_time = time.time()
                    if current_time - last_save_time >= self.auto_save_interval:
                        f.flush()
                        last_save_time = current_time
                        self.logger.debug(f"Auto-saved data for stream: {stream_name}")
        
        except Exception as e:
            self.logger.error(f"Error recording stream {stream_name}: {e}")
        
        finally:
            self.logger.info(f"Stopped recording stream: {stream_name}")
    
    def log_event(self, event_type: str, task_name: str, event_data: Dict[str, Any]):
        """
        Log an experiment event.
        
        Args:
            event_type: Type of event (e.g., 'task_start', 'stimulus', 'response')
            task_name: Name of the task or component
            event_data: Additional event data
        """
        if not self.current_session:
            self.logger.warning("No active session for event logging")
            return
        
        timestamp = time.time()
        
        # Create event
        event = TaskEvent(
            timestamp=timestamp,
            event_type=event_type,
            task_name=task_name,
            event_data=event_data,
            participant_id=self.current_session.participant_id,
            session_id=self.current_session.session_id
        )
        
        # Store event
        with self.event_lock:
            self.events.append(event)
        
        # Send via LSL if available
        if self.event_outlet:
            try:
                event_json = json.dumps({
                    'timestamp': timestamp,
                    'event_type': event_type,
                    'task_name': task_name,
                    'event_data': event_data,
                    'participant_id': self.current_session.participant_id,
                    'session_id': self.current_session.session_id
                })
                self.event_outlet.push_sample([event_json])
            except Exception as e:
                self.logger.error(f"Failed to send event via LSL: {e}")
        
        self.logger.debug(f"Logged event: {event_type} in {task_name}")
    
    def stop_recording(self):
        """Stop recording all streams."""
        if not self.is_recording:
            return
        
        try:
            self.logger.info("Stopping data recording...")
            
            # Signal all threads to stop
            self.stop_event.set()
            
            # Wait for threads to finish
            for stream_name, thread in self.recording_threads.items():
                if thread.is_alive():
                    thread.join(timeout=2.0)
                    if thread.is_alive():
                        self.logger.warning(f"Recording thread for {stream_name} did not stop gracefully")
            
            # Close inlets
            for inlet in self.data_inlets.values():
                try:
                    inlet.close_stream()
                except:
                    pass
            
            self.data_inlets.clear()
            self.recording_threads.clear()
            self.is_recording = False
            
            # Log recording stop event
            self.log_event('recording_stop', 'system', {
                'total_events': len(self.events),
                'recording_files': self.current_session.recording_files if self.current_session else {}
            })
            
            self.logger.info("Data recording stopped")
            
        except Exception as e:
            self.logger.error(f"Error stopping recording: {e}")
    
    def end_session(self):
        """End the current experiment session."""
        if not self.current_session:
            return
        
        try:
            # Stop recording if active
            if self.is_recording:
                self.stop_recording()
            
            # Update session end time
            self.current_session.end_time = datetime.now()
            
            # Save session metadata and events
            self._save_session_data()
            
            # Log session end
            self.log_event('session_end', 'experiment', {
                'end_time': self.current_session.end_time.isoformat(),
                'duration_seconds': (self.current_session.end_time - self.current_session.start_time).total_seconds(),
                'total_events': len(self.events)
            })
            
            self.logger.info(f"Ended experiment session: {self.current_session.participant_id}/{self.current_session.session_id}")
            
            # Cleanup
            if self.event_outlet:
                del self.event_outlet
                self.event_outlet = None
            
            self.current_session = None
            
        except Exception as e:
            self.logger.error(f"Error ending session: {e}")
    
    def _save_session_data(self):
        """Save session metadata and events to files."""
        if not self.current_session:
            return
        
        try:
            # Save session metadata
            session_file = os.path.join(self.current_session.data_directory, 'session_info.json')
            with open(session_file, 'w') as f:
                session_dict = asdict(self.current_session)
                # Convert datetime objects to strings
                session_dict['start_time'] = self.current_session.start_time.isoformat()
                if self.current_session.end_time:
                    session_dict['end_time'] = self.current_session.end_time.isoformat()
                json.dump(session_dict, f, indent=2)
            
            # Save events
            events_file = os.path.join(self.current_session.data_directory, 'events.json')
            with open(events_file, 'w') as f:
                events_dict = [asdict(event) for event in self.events]
                json.dump(events_dict, f, indent=2)
            
            # Save events as CSV for easy analysis
            events_csv = os.path.join(self.current_session.data_directory, 'events.csv')
            with open(events_csv, 'w') as f:
                f.write("timestamp,event_type,task_name,participant_id,session_id,event_data\n")
                for event in self.events:
                    event_data_str = json.dumps(event.event_data).replace(',', ';')  # Avoid CSV conflicts
                    f.write(f"{event.timestamp},{event.event_type},{event.task_name},"
                           f"{event.participant_id},{event.session_id},\"{event_data_str}\"\n")
            
            self.logger.info(f"Saved session data to: {self.current_session.data_directory}")
            
        except Exception as e:
            self.logger.error(f"Error saving session data: {e}")
    
    def get_session_status(self) -> Dict[str, Any]:
        """Get current session status."""
        if not self.current_session:
            return {'active_session': False}
        
        return {
            'active_session': True,
            'participant_id': self.current_session.participant_id,
            'session_id': self.current_session.session_id,
            'start_time': self.current_session.start_time.isoformat(),
            'is_recording': self.is_recording,
            'recorded_streams': list(self.data_inlets.keys()),
            'total_events': len(self.events),
            'data_directory': self.current_session.data_directory,
            'recording_files': self.current_session.recording_files
        }

# Global recorder instance
_global_recorder: Optional[ExperimentDataRecorder] = None

def get_experiment_recorder() -> ExperimentDataRecorder:
    """Get the global experiment recorder instance."""
    global _global_recorder
    if _global_recorder is None:
        _global_recorder = ExperimentDataRecorder()
    return _global_recorder

def log_experiment_event(event_type: str, task_name: str, event_data: Dict[str, Any]):
    """Convenience function to log an experiment event."""
    recorder = get_experiment_recorder()
    recorder.log_event(event_type, task_name, event_data)

def main():
    """Test the experiment data recorder."""
    print("Testing Experiment Data Recorder...")
    
    if not LSL_AVAILABLE:
        print("LSL not available, cannot test recorder")
        return
    
    # Create recorder
    recorder = ExperimentDataRecorder()
    
    try:
        # Start session
        session = recorder.start_session("test_participant", "test_session_001")
        print(f"Started session: {session.participant_id}/{session.session_id}")
        
        # Start recording
        if recorder.start_recording():
            print("Recording started")
            
            # Log some test events
            recorder.log_event('test_start', 'test_task', {'test_parameter': 'value1'})
            time.sleep(2)
            recorder.log_event('stimulus', 'test_task', {'stimulus_type': 'visual', 'intensity': 0.8})
            time.sleep(1)
            recorder.log_event('response', 'test_task', {'response_key': 'left', 'reaction_time': 0.543})
            time.sleep(2)
            recorder.log_event('test_end', 'test_task', {'success': True})
            
            print("Logged test events")
            
            # Stop recording
            recorder.stop_recording()
            print("Recording stopped")
        
        # End session
        recorder.end_session()
        print("Session ended")
        
        print("Experiment Data Recorder test completed!")
        
    except Exception as e:
        print(f"Error in test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 