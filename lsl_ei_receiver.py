#!/usr/bin/env python3
"""
LSL E/I Receiver
Receives E/I ratio data from LSL streams and forwards it to the existing visualization system.
This module acts as a bridge between LSL streams and the existing TCP-based visualization.
"""

import time
import socket
import threading
import signal
import sys
from typing import Optional, Dict, Any, List
import traceback

try:
    import pylsl
    from pylsl import resolve_stream, StreamInlet
except ImportError:
    print("Error: pylsl not installed. Install with: pip install pylsl")
    sys.exit(1)

from config import get_config
from logger import get_logger

logger = get_logger("LSL_EI_Receiver")

class LSLEIReceiver:
    """
    LSL E/I Receiver for subscribing to E/I ratio streams.
    
    This class handles:
    1. LSL stream discovery and connection
    2. Real-time data reception
    3. Data forwarding to visualization system
    4. Connection management and error recovery
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the LSL E/I Receiver.
        
        Args:
            config: Configuration dictionary with LSL and forwarding settings
        """
        self.config = config or self._load_default_config()
        self.logger = logger
        
        # LSL stream parameters
        self.stream_name = self.config.get('lsl_stream_name', 'FSL-MRS-EI-Ratio')
        self.stream_type = self.config.get('lsl_stream_type', 'EI_Ratio')
        self.source_id = self.config.get('lsl_source_id', None)
        
        # Forwarding parameters
        self.forward_host = self.config.get('forward_host', '127.0.0.1')
        self.forward_port = self.config.get('forward_port', 5005)
        self.forward_enabled = self.config.get('forward_enabled', True)
        
        # Control variables
        self.is_receiving = False
        self.receive_thread = None
        self.inlet = None
        self.stop_event = threading.Event()
        
        # Connection management
        self.forward_socket = None
        self.last_connection_attempt = 0
        self.connection_retry_interval = self.config.get('connection_retry_interval', 5.0)
        
        # Data tracking
        self.last_ei_ratio = None
        self.samples_received = 0
        self.last_sample_time = None
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
    def _load_default_config(self) -> Dict[str, Any]:
        """Load default configuration."""
        try:
            return {
                'lsl_stream_name': get_config('lsl_ei_receiver.stream_name', 'FSL-MRS-EI-Ratio'),
                'lsl_stream_type': get_config('lsl_ei_receiver.stream_type', 'EI_Ratio'),
                'lsl_source_id': get_config('lsl_ei_receiver.source_id', None),
                'forward_host': get_config('lsl_ei_receiver.forward_host', '127.0.0.1'),
                'forward_port': get_config('lsl_ei_receiver.forward_port', 5005),
                'forward_enabled': get_config('lsl_ei_receiver.forward_enabled', True),
                'connection_retry_interval': get_config('lsl_ei_receiver.connection_retry_interval', 5.0),
                'stream_resolve_timeout': get_config('lsl_ei_receiver.stream_resolve_timeout', 5.0),
                'buffer_length': get_config('lsl_ei_receiver.buffer_length', 360),  # seconds
                'max_chunk_length': get_config('lsl_ei_receiver.max_chunk_length', 0),  # 0 = no chunking
            }
        except Exception as e:
            self.logger.warning(f"Could not load config, using defaults: {e}")
            return {
                'lsl_stream_name': 'FSL-MRS-EI-Ratio',
                'lsl_stream_type': 'EI_Ratio',
                'lsl_source_id': None,
                'forward_host': '127.0.0.1',
                'forward_port': 5005,
                'forward_enabled': True,
                'connection_retry_interval': 5.0,
                'stream_resolve_timeout': 5.0,
                'buffer_length': 360,
                'max_chunk_length': 0,
            }
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        self.logger.info(f"Received signal {signum}, shutting down...")
        self.stop_receiving()
        sys.exit(0)
    
    def discover_streams(self) -> List[Any]:
        """
        Discover available LSL streams matching our criteria.
        
        Returns:
            List of stream info objects
        """
        try:
            self.logger.info(f"Looking for LSL streams...")
            
            # Build search criteria
            search_criteria = []
            if self.stream_name:
                search_criteria.append(f"name='{self.stream_name}'")
            if self.stream_type:
                search_criteria.append(f"type='{self.stream_type}'")
            if self.source_id:
                search_criteria.append(f"source_id='{self.source_id}'")
            
            # Resolve streams
            timeout = self.config.get('stream_resolve_timeout', 5.0)
            
            if search_criteria:
                # Use specific criteria
                query = " and ".join(search_criteria)
                self.logger.info(f"Searching for streams with criteria: {query}")
                streams = resolve_stream('name', self.stream_name, timeout=timeout)
            else:
                # Get all streams
                self.logger.info("Searching for all available streams")
                streams = resolve_stream(timeout=timeout)
            
            self.logger.info(f"Found {len(streams)} matching stream(s)")
            
            # Log stream details
            for i, stream in enumerate(streams):
                self.logger.info(f"Stream {i+1}: name='{stream.name()}', "
                               f"type='{stream.type()}', "
                               f"source_id='{stream.source_id()}', "
                               f"channels={stream.channel_count()}, "
                               f"rate={stream.nominal_srate()}Hz")
            
            return streams
            
        except Exception as e:
            self.logger.error(f"Error discovering streams: {e}")
            return []
    
    def connect_to_stream(self) -> bool:
        """
        Connect to the LSL stream.
        
        Returns:
            bool: True if connected successfully, False otherwise
        """
        try:
            # Discover streams
            streams = self.discover_streams()
            if not streams:
                self.logger.warning("No matching streams found")
                return False
            
            # Use the first matching stream
            stream_info = streams[0]
            self.logger.info(f"Connecting to stream: {stream_info.name()}")
            
            # Create inlet
            buffer_length = self.config.get('buffer_length', 360)
            max_chunk_length = self.config.get('max_chunk_length', 0)
            
            self.inlet = StreamInlet(
                stream_info,
                buffer_length=buffer_length,
                max_chunklen=max_chunk_length
            )
            
            # Open the stream
            self.inlet.open_stream()
            
            self.logger.info(f"Successfully connected to LSL stream '{stream_info.name()}'")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to connect to LSL stream: {e}")
            traceback.print_exc()
            return False
    
    def setup_forwarding(self) -> bool:
        """
        Setup TCP forwarding connection.
        
        Returns:
            bool: True if setup successful, False otherwise
        """
        if not self.forward_enabled:
            self.logger.info("Forwarding disabled")
            return True
        
        try:
            current_time = time.time()
            
            # Check if we should retry connection
            if (self.forward_socket is None and 
                current_time - self.last_connection_attempt >= self.connection_retry_interval):
                
                self.last_connection_attempt = current_time
                
                self.logger.info(f"Attempting to connect to visualization at "
                               f"{self.forward_host}:{self.forward_port}")
                
                # Create socket
                self.forward_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.forward_socket.settimeout(2.0)
                
                try:
                    self.forward_socket.connect((self.forward_host, self.forward_port))
                    self.logger.info("Successfully connected to visualization system")
                    return True
                    
                except (ConnectionRefusedError, socket.timeout, OSError) as e:
                    self.logger.warning(f"Could not connect to visualization: {e}")
                    if self.forward_socket:
                        self.forward_socket.close()
                        self.forward_socket = None
                    return False
            
            return self.forward_socket is not None
            
        except Exception as e:
            self.logger.error(f"Error setting up forwarding: {e}")
            if self.forward_socket:
                self.forward_socket.close()
                self.forward_socket = None
            return False
    
    def forward_data(self, ei_ratio: float) -> bool:
        """
        Forward E/I ratio data to the visualization system.
        
        Args:
            ei_ratio: E/I ratio value to forward
            
        Returns:
            bool: True if forwarded successfully, False otherwise
        """
        if not self.forward_enabled:
            return True
        
        try:
            # Ensure we have a connection
            if not self.setup_forwarding():
                return False
            
            # Format data (compatible with existing visualization)
            data_str = f"{ei_ratio:.6f}\n"
            
            # Send data
            self.forward_socket.sendall(data_str.encode())
            self.logger.debug(f"Forwarded E/I ratio: {ei_ratio:.3f}")
            return True
            
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError, OSError) as e:
            self.logger.warning(f"Connection to visualization lost: {e}")
            if self.forward_socket:
                self.forward_socket.close()
                self.forward_socket = None
            return False
            
        except Exception as e:
            self.logger.error(f"Error forwarding data: {e}")
            return False
    
    def receive_data(self):
        """Main receiving loop that runs in a separate thread."""
        self.logger.info("Starting E/I ratio reception...")
        
        while not self.stop_event.is_set():
            try:
                if not self.inlet:
                    # Try to connect
                    if self.connect_to_stream():
                        continue
                    else:
                        # Wait before retrying
                        time.sleep(1.0)
                        continue
                
                # Pull sample from LSL stream
                sample, timestamp = self.inlet.pull_sample(timeout=1.0)
                
                if sample is not None:
                    # Extract E/I ratio (assuming single channel)
                    ei_ratio = float(sample[0])
                    
                    # Update tracking
                    self.last_ei_ratio = ei_ratio
                    self.samples_received += 1
                    self.last_sample_time = timestamp
                    
                    # Forward to visualization
                    self.forward_data(ei_ratio)
                    
                    self.logger.debug(f"Received E/I ratio: {ei_ratio:.3f} at {timestamp:.3f}")
                
            except Exception as e:
                self.logger.error(f"Error in receiving loop: {e}")
                traceback.print_exc()
                
                # Reset connection on error
                if self.inlet:
                    try:
                        self.inlet.close_stream()
                    except:
                        pass
                    self.inlet = None
                
                # Brief pause before retrying
                time.sleep(1.0)
    
    def start_receiving(self) -> bool:
        """
        Start receiving E/I ratio data.
        
        Returns:
            bool: True if started successfully, False otherwise
        """
        if self.is_receiving:
            self.logger.warning("Already receiving")
            return True
        
        try:
            # Start receiving thread
            self.stop_event.clear()
            self.receive_thread = threading.Thread(target=self.receive_data, daemon=True)
            self.receive_thread.start()
            
            self.is_receiving = True
            self.logger.info("E/I ratio reception started successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start receiving: {e}")
            traceback.print_exc()
            return False
    
    def stop_receiving(self):
        """Stop receiving E/I ratio data."""
        if not self.is_receiving:
            return
        
        try:
            self.logger.info("Stopping E/I ratio reception...")
            
            # Signal stop and wait for thread
            self.stop_event.set()
            if self.receive_thread and self.receive_thread.is_alive():
                self.receive_thread.join(timeout=2.0)
            
            # Cleanup LSL connection
            if self.inlet:
                try:
                    self.inlet.close_stream()
                except:
                    pass
                self.inlet = None
            
            # Cleanup forwarding connection
            if self.forward_socket:
                try:
                    self.forward_socket.close()
                except:
                    pass
                self.forward_socket = None
            
            self.is_receiving = False
            self.logger.info("E/I ratio reception stopped")
            
        except Exception as e:
            self.logger.error(f"Error stopping reception: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get current status information.
        
        Returns:
            dict: Status information
        """
        return {
            'is_receiving': self.is_receiving,
            'stream_name': self.stream_name,
            'stream_type': self.stream_type,
            'forward_host': self.forward_host,
            'forward_port': self.forward_port,
            'forward_enabled': self.forward_enabled,
            'last_ei_ratio': self.last_ei_ratio,
            'samples_received': self.samples_received,
            'last_sample_time': self.last_sample_time,
            'connected_to_stream': self.inlet is not None,
            'connected_to_visualization': self.forward_socket is not None,
        }

def main():
    """Main function for running the receiver as a standalone script."""
    import argparse
    
    parser = argparse.ArgumentParser(description='LSL E/I Receiver')
    parser.add_argument('--config', type=str, help='Path to configuration file')
    parser.add_argument('--stream-name', type=str, default='FSL-MRS-EI-Ratio',
                       help='LSL stream name to subscribe to')
    parser.add_argument('--forward-host', type=str, default='127.0.0.1',
                       help='Host to forward data to')
    parser.add_argument('--forward-port', type=int, default=5005,
                       help='Port to forward data to')
    parser.add_argument('--no-forward', action='store_true',
                       help='Disable data forwarding')
    
    args = parser.parse_args()
    
    # Build config from arguments
    config = {
        'lsl_stream_name': args.stream_name,
        'forward_host': args.forward_host,
        'forward_port': args.forward_port,
        'forward_enabled': not args.no_forward,
    }
    
    # Create and start receiver
    receiver = LSLEIReceiver(config)
    
    try:
        if receiver.start_receiving():
            logger.info("Receiver started. Press Ctrl+C to stop.")
            
            # Keep running until interrupted
            while True:
                time.sleep(5)
                status = receiver.get_status()
                logger.info(f"Status: Receiving={status['is_receiving']}, "
                          f"Samples={status['samples_received']}, "
                          f"Last E/I={status['last_ei_ratio']}, "
                          f"LSL Connected={status['connected_to_stream']}, "
                          f"Viz Connected={status['connected_to_visualization']}")
                
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        traceback.print_exc()
    finally:
        receiver.stop_receiving()

if __name__ == "__main__":
    main() 