#!/usr/bin/env python3
"""
Task LSL Publishers
LSL publishers for M1 tapping task and V1 orientation task to stream task data and responses.
"""

import time
import threading
import json
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

try:
    import pylsl
    from pylsl import StreamInfo, StreamOutlet
    LSL_AVAILABLE = True
except ImportError:
    print("Warning: pylsl not available. Install with: pip install pylsl")
    LSL_AVAILABLE = False

from logger import get_logger

logger = get_logger("TaskLSLPublishers")

@dataclass
class M1TappingEvent:
    """M1 tapping task event data."""
    timestamp: float
    event_type: str  # 'sequence_start', 'tap', 'sequence_end', 'trial_start', 'trial_end'
    trial_number: int
    sequence_position: Optional[int] = None
    target_key: Optional[str] = None
    pressed_key: Optional[str] = None
    reaction_time: Optional[float] = None
    is_correct: Optional[bool] = None
    sequence: Optional[List[str]] = None

@dataclass
class V1OrientationEvent:
    """V1 orientation task event data."""
    timestamp: float
    event_type: str  # 'trial_start', 'stimulus_on', 'stimulus_off', 'response', 'trial_end'
    trial_number: int
    stimulus_orientation: Optional[float] = None
    stimulus_duration: Optional[float] = None
    response_key: Optional[str] = None
    reaction_time: Optional[float] = None
    is_correct: Optional[bool] = None

class M1TappingLSLPublisher:
    """LSL publisher for M1 tapping task data."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize M1 tapping LSL publisher."""
        if not LSL_AVAILABLE:
            raise ImportError("LSL is required. Install with: pip install pylsl")
        
        self.config = config or {}
        self.logger = logger
        
        # Stream configuration
        self.stream_name = self.config.get('stream_name', 'M1-Tapping-Task')
        self.stream_type = self.config.get('stream_type', 'TaskData')
        self.source_id = self.config.get('source_id', 'm1-tapping-001')
        
        # LSL outlet
        self.outlet: Optional[StreamOutlet] = None
        self.is_active = False
        
        self._setup_stream()
    
    def _setup_stream(self):
        """Setup the LSL stream."""
        try:
            # Create stream info
            info = StreamInfo(
                name=self.stream_name,
                type=self.stream_type,
                channel_count=1,
                nominal_srate=0,  # Irregular sampling
                channel_format=pylsl.cf_string,
                source_id=self.source_id
            )
            
            # Add metadata
            desc = info.desc()
            desc.append_child_value("manufacturer", "RealtimeMRS")
            desc.append_child_value("unit", "event")
            desc.append_child_value("description", "M1 tapping task events and responses")
            desc.append_child_value("task_type", "motor_tapping")
            
            # Add channel information
            channels = desc.append_child("channels")
            ch = channels.append_child("channel")
            ch.append_child_value("label", "TaskEvent")
            ch.append_child_value("unit", "string")
            ch.append_child_value("type", "TaskEvent")
            
            self.outlet = StreamOutlet(info)
            self.is_active = True
            self.logger.info(f"M1 tapping LSL stream '{self.stream_name}' created successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to setup M1 tapping LSL stream: {e}")
            raise
    
    def publish_event(self, event: M1TappingEvent):
        """Publish an M1 tapping event."""
        if not self.is_active or not self.outlet:
            self.logger.warning("M1 tapping LSL stream not active")
            return
        
        try:
            # Convert event to JSON
            event_dict = {
                'timestamp': event.timestamp,
                'event_type': event.event_type,
                'trial_number': event.trial_number,
                'sequence_position': event.sequence_position,
                'target_key': event.target_key,
                'pressed_key': event.pressed_key,
                'reaction_time': event.reaction_time,
                'is_correct': event.is_correct,
                'sequence': event.sequence,
                'task_type': 'm1_tapping'
            }
            
            event_json = json.dumps(event_dict)
            self.outlet.push_sample([event_json])
            
            self.logger.debug(f"Published M1 event: {event.event_type} (trial {event.trial_number})")
            
        except Exception as e:
            self.logger.error(f"Failed to publish M1 tapping event: {e}")
    
    def trial_start(self, trial_number: int, sequence: List[str]):
        """Log trial start."""
        event = M1TappingEvent(
            timestamp=time.time(),
            event_type='trial_start',
            trial_number=trial_number,
            sequence=sequence
        )
        self.publish_event(event)
    
    def sequence_start(self, trial_number: int, sequence: List[str]):
        """Log sequence start."""
        event = M1TappingEvent(
            timestamp=time.time(),
            event_type='sequence_start',
            trial_number=trial_number,
            sequence=sequence
        )
        self.publish_event(event)
    
    def tap_event(self, trial_number: int, sequence_position: int, target_key: str, 
                  pressed_key: str, reaction_time: float, is_correct: bool):
        """Log a tap event."""
        event = M1TappingEvent(
            timestamp=time.time(),
            event_type='tap',
            trial_number=trial_number,
            sequence_position=sequence_position,
            target_key=target_key,
            pressed_key=pressed_key,
            reaction_time=reaction_time,
            is_correct=is_correct
        )
        self.publish_event(event)
    
    def sequence_end(self, trial_number: int):
        """Log sequence end."""
        event = M1TappingEvent(
            timestamp=time.time(),
            event_type='sequence_end',
            trial_number=trial_number
        )
        self.publish_event(event)
    
    def trial_end(self, trial_number: int):
        """Log trial end."""
        event = M1TappingEvent(
            timestamp=time.time(),
            event_type='trial_end',
            trial_number=trial_number
        )
        self.publish_event(event)
    
    def close(self):
        """Close the LSL stream."""
        if self.outlet:
            del self.outlet
            self.outlet = None
        self.is_active = False
        self.logger.info("M1 tapping LSL stream closed")

class V1OrientationLSLPublisher:
    """LSL publisher for V1 orientation task data."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize V1 orientation LSL publisher."""
        if not LSL_AVAILABLE:
            raise ImportError("LSL is required. Install with: pip install pylsl")
        
        self.config = config or {}
        self.logger = logger
        
        # Stream configuration
        self.stream_name = self.config.get('stream_name', 'V1-Orientation-Task')
        self.stream_type = self.config.get('stream_type', 'TaskData')
        self.source_id = self.config.get('source_id', 'v1-orientation-001')
        
        # LSL outlet
        self.outlet: Optional[StreamOutlet] = None
        self.is_active = False
        
        self._setup_stream()
    
    def _setup_stream(self):
        """Setup the LSL stream."""
        try:
            # Create stream info
            info = StreamInfo(
                name=self.stream_name,
                type=self.stream_type,
                channel_count=1,
                nominal_srate=0,  # Irregular sampling
                channel_format=pylsl.cf_string,
                source_id=self.source_id
            )
            
            # Add metadata
            desc = info.desc()
            desc.append_child_value("manufacturer", "RealtimeMRS")
            desc.append_child_value("unit", "event")
            desc.append_child_value("description", "V1 orientation task events and responses")
            desc.append_child_value("task_type", "visual_orientation")
            
            # Add channel information
            channels = desc.append_child("channels")
            ch = channels.append_child("channel")
            ch.append_child_value("label", "TaskEvent")
            ch.append_child_value("unit", "string")
            ch.append_child_value("type", "TaskEvent")
            
            self.outlet = StreamOutlet(info)
            self.is_active = True
            self.logger.info(f"V1 orientation LSL stream '{self.stream_name}' created successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to setup V1 orientation LSL stream: {e}")
            raise
    
    def publish_event(self, event: V1OrientationEvent):
        """Publish a V1 orientation event."""
        if not self.is_active or not self.outlet:
            self.logger.warning("V1 orientation LSL stream not active")
            return
        
        try:
            # Convert event to JSON
            event_dict = {
                'timestamp': event.timestamp,
                'event_type': event.event_type,
                'trial_number': event.trial_number,
                'stimulus_orientation': event.stimulus_orientation,
                'stimulus_duration': event.stimulus_duration,
                'response_key': event.response_key,
                'reaction_time': event.reaction_time,
                'is_correct': event.is_correct,
                'task_type': 'v1_orientation'
            }
            
            event_json = json.dumps(event_dict)
            self.outlet.push_sample([event_json])
            
            self.logger.debug(f"Published V1 event: {event.event_type} (trial {event.trial_number})")
            
        except Exception as e:
            self.logger.error(f"Failed to publish V1 orientation event: {e}")
    
    def trial_start(self, trial_number: int):
        """Log trial start."""
        event = V1OrientationEvent(
            timestamp=time.time(),
            event_type='trial_start',
            trial_number=trial_number
        )
        self.publish_event(event)
    
    def stimulus_on(self, trial_number: int, orientation: float, duration: float):
        """Log stimulus onset."""
        event = V1OrientationEvent(
            timestamp=time.time(),
            event_type='stimulus_on',
            trial_number=trial_number,
            stimulus_orientation=orientation,
            stimulus_duration=duration
        )
        self.publish_event(event)
    
    def stimulus_off(self, trial_number: int):
        """Log stimulus offset."""
        event = V1OrientationEvent(
            timestamp=time.time(),
            event_type='stimulus_off',
            trial_number=trial_number
        )
        self.publish_event(event)
    
    def response_event(self, trial_number: int, response_key: str, reaction_time: float, 
                      is_correct: bool):
        """Log a response event."""
        event = V1OrientationEvent(
            timestamp=time.time(),
            event_type='response',
            trial_number=trial_number,
            response_key=response_key,
            reaction_time=reaction_time,
            is_correct=is_correct
        )
        self.publish_event(event)
    
    def trial_end(self, trial_number: int):
        """Log trial end."""
        event = V1OrientationEvent(
            timestamp=time.time(),
            event_type='trial_end',
            trial_number=trial_number
        )
        self.publish_event(event)
    
    def close(self):
        """Close the LSL stream."""
        if self.outlet:
            del self.outlet
            self.outlet = None
        self.is_active = False
        self.logger.info("V1 orientation LSL stream closed")

class PhysiologicalDataPublisher:
    """LSL publisher for physiological data (heart rate, eye tracking, etc.)."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize physiological data LSL publisher."""
        if not LSL_AVAILABLE:
            raise ImportError("LSL is required. Install with: pip install pylsl")
        
        self.config = config or {}
        self.logger = logger
        
        # Stream configuration
        self.stream_name = self.config.get('stream_name', 'Physiological-Data')
        self.stream_type = self.config.get('stream_type', 'Physiological')
        self.source_id = self.config.get('source_id', 'physio-001')
        self.sampling_rate = self.config.get('sampling_rate', 100.0)  # Hz
        
        # Data channels
        self.channels = self.config.get('channels', [
            'heart_rate', 'eye_x', 'eye_y', 'pupil_diameter', 'blink'
        ])
        
        # LSL outlet
        self.outlet: Optional[StreamOutlet] = None
        self.is_active = False
        
        self._setup_stream()
    
    def _setup_stream(self):
        """Setup the LSL stream."""
        try:
            # Create stream info
            info = StreamInfo(
                name=self.stream_name,
                type=self.stream_type,
                channel_count=len(self.channels),
                nominal_srate=self.sampling_rate,
                channel_format=pylsl.cf_float32,
                source_id=self.source_id
            )
            
            # Add metadata
            desc = info.desc()
            desc.append_child_value("manufacturer", "RealtimeMRS")
            desc.append_child_value("unit", "mixed")
            desc.append_child_value("description", "Physiological monitoring data")
            
            # Add channel information
            channels_desc = desc.append_child("channels")
            for i, channel_name in enumerate(self.channels):
                ch = channels_desc.append_child("channel")
                ch.append_child_value("label", channel_name)
                
                # Set appropriate units
                if channel_name == 'heart_rate':
                    ch.append_child_value("unit", "bpm")
                elif channel_name in ['eye_x', 'eye_y']:
                    ch.append_child_value("unit", "pixels")
                elif channel_name == 'pupil_diameter':
                    ch.append_child_value("unit", "mm")
                elif channel_name == 'blink':
                    ch.append_child_value("unit", "binary")
                else:
                    ch.append_child_value("unit", "unknown")
                
                ch.append_child_value("type", "Physiological")
            
            self.outlet = StreamOutlet(info)
            self.is_active = True
            self.logger.info(f"Physiological LSL stream '{self.stream_name}' created successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to setup physiological LSL stream: {e}")
            raise
    
    def publish_sample(self, data: Dict[str, float]):
        """Publish a physiological data sample."""
        if not self.is_active or not self.outlet:
            self.logger.warning("Physiological LSL stream not active")
            return
        
        try:
            # Create sample array in channel order
            sample = []
            for channel_name in self.channels:
                value = data.get(channel_name, 0.0)
                sample.append(float(value))
            
            self.outlet.push_sample(sample)
            
        except Exception as e:
            self.logger.error(f"Failed to publish physiological sample: {e}")
    
    def close(self):
        """Close the LSL stream."""
        if self.outlet:
            del self.outlet
            self.outlet = None
        self.is_active = False
        self.logger.info("Physiological LSL stream closed")

# Global publisher instances
_m1_publisher: Optional[M1TappingLSLPublisher] = None
_v1_publisher: Optional[V1OrientationLSLPublisher] = None
_physio_publisher: Optional[PhysiologicalDataPublisher] = None

def get_m1_publisher() -> M1TappingLSLPublisher:
    """Get the global M1 tapping LSL publisher."""
    global _m1_publisher
    if _m1_publisher is None:
        _m1_publisher = M1TappingLSLPublisher()
    return _m1_publisher

def get_v1_publisher() -> V1OrientationLSLPublisher:
    """Get the global V1 orientation LSL publisher."""
    global _v1_publisher
    if _v1_publisher is None:
        _v1_publisher = V1OrientationLSLPublisher()
    return _v1_publisher

def get_physio_publisher() -> PhysiologicalDataPublisher:
    """Get the global physiological data LSL publisher."""
    global _physio_publisher
    if _physio_publisher is None:
        _physio_publisher = PhysiologicalDataPublisher()
    return _physio_publisher

def cleanup_publishers():
    """Cleanup all global publishers."""
    global _m1_publisher, _v1_publisher, _physio_publisher
    
    if _m1_publisher:
        _m1_publisher.close()
        _m1_publisher = None
    
    if _v1_publisher:
        _v1_publisher.close()
        _v1_publisher = None
    
    if _physio_publisher:
        _physio_publisher.close()
        _physio_publisher = None

def main():
    """Test the task LSL publishers."""
    print("Testing Task LSL Publishers...")
    
    if not LSL_AVAILABLE:
        print("LSL not available, cannot test publishers")
        return
    
    try:
        # Test M1 publisher
        print("Testing M1 tapping publisher...")
        m1_pub = M1TappingLSLPublisher()
        
        m1_pub.trial_start(1, ['1', '2', '3', '4'])
        time.sleep(0.1)
        m1_pub.sequence_start(1, ['1', '2', '3', '4'])
        time.sleep(0.1)
        m1_pub.tap_event(1, 0, '1', '1', 0.234, True)
        time.sleep(0.1)
        m1_pub.tap_event(1, 1, '2', '2', 0.187, True)
        time.sleep(0.1)
        m1_pub.sequence_end(1)
        time.sleep(0.1)
        m1_pub.trial_end(1)
        
        print("M1 publisher test completed")
        
        # Test V1 publisher
        print("Testing V1 orientation publisher...")
        v1_pub = V1OrientationLSLPublisher()
        
        v1_pub.trial_start(1)
        time.sleep(0.1)
        v1_pub.stimulus_on(1, 45.0, 0.1)
        time.sleep(0.1)
        v1_pub.stimulus_off(1)
        time.sleep(0.1)
        v1_pub.response_event(1, 'left', 0.456, True)
        time.sleep(0.1)
        v1_pub.trial_end(1)
        
        print("V1 publisher test completed")
        
        # Test physiological publisher
        print("Testing physiological publisher...")
        physio_pub = PhysiologicalDataPublisher()
        
        for i in range(5):
            physio_data = {
                'heart_rate': 72.0 + i,
                'eye_x': 512.0,
                'eye_y': 384.0,
                'pupil_diameter': 3.5,
                'blink': 0.0
            }
            physio_pub.publish_sample(physio_data)
            time.sleep(0.01)  # 100 Hz
        
        print("Physiological publisher test completed")
        
        # Cleanup
        m1_pub.close()
        v1_pub.close()
        physio_pub.close()
        
        print("Task LSL Publishers test completed!")
        
    except Exception as e:
        print(f"Error in test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 