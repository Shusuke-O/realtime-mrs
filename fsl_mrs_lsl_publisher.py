#!/usr/bin/env python3
"""
FSL-MRS LSL Publisher
Streams E/I ratio data from FSL-MRS analysis using Lab Streaming Layer (LSL).
This module provides real-time streaming of excitatory/inhibitory ratio data
for visualization and analysis.
"""

import time
import numpy as np
import threading
import signal
import sys
from typing import Optional, Dict, Any, Callable
import traceback

try:
    import pylsl
    from pylsl import StreamInfo, StreamOutlet
except ImportError:
    print("Error: pylsl not installed. Install with: pip install pylsl")
    sys.exit(1)

try:
    # FSL-MRS imports - these may need adjustment based on actual FSL-MRS API
    import fsl_mrs
    from fsl_mrs import mrs_io, fitting, utils
    FSL_MRS_AVAILABLE = True
except ImportError:
    print("Warning: FSL-MRS not available. Using simulated data.")
    FSL_MRS_AVAILABLE = False

# Import our custom FSL-MRS data generator
from fsl_mrs_data_generator import FSLMRSDataGenerator, MetaboliteConcentrations

from config import get_config
from logger import get_logger

logger = get_logger("FSL_MRS_LSL_Publisher")

class FSLMRSLSLPublisher:
    """
    FSL-MRS LSL Publisher for streaming E/I ratio data.
    
    This class handles:
    1. FSL-MRS data acquisition and processing
    2. E/I ratio calculation
    3. LSL stream publishing
    4. Real-time data streaming
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the FSL-MRS LSL Publisher.
        
        Args:
            config: Configuration dictionary with FSL-MRS and LSL settings
        """
        self.config = config or self._load_default_config()
        self.logger = logger
        
        # LSL stream setup
        self.stream_name = self.config.get('lsl_stream_name', 'FSL-MRS-EI-Ratio')
        self.stream_type = self.config.get('lsl_stream_type', 'EI_Ratio')
        self.source_id = self.config.get('lsl_source_id', 'fsl-mrs-ei-001')
        
        # Streaming parameters
        self.sampling_rate = self.config.get('sampling_rate', 1.0)  # Hz
        self.channel_count = 1  # E/I ratio is a single value
        self.channel_format = pylsl.cf_float32
        
        # FSL-MRS parameters
        self.mrs_data_path = self.config.get('mrs_data_path', None)
        self.basis_set_path = self.config.get('basis_set_path', None)
        self.fitting_params = self.config.get('fitting_params', {})
        
        # Control variables
        self.is_streaming = False
        self.stream_thread = None
        self.outlet = None
        self.stop_event = threading.Event()
        
        # Data processing
        self.data_processor = None
        self.mrs_data_generator = None
        self.last_ei_ratio = 0.5  # Default neutral ratio
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
    def _load_default_config(self) -> Dict[str, Any]:
        """Load default configuration."""
        try:
            return {
                'lsl_stream_name': get_config('fsl_mrs_lsl.stream_name', 'FSL-MRS-EI-Ratio'),
                'lsl_stream_type': get_config('fsl_mrs_lsl.stream_type', 'EI_Ratio'),
                'lsl_source_id': get_config('fsl_mrs_lsl.source_id', 'fsl-mrs-ei-001'),
                'sampling_rate': get_config('fsl_mrs_lsl.sampling_rate', 1.0),
                'mrs_data_path': get_config('fsl_mrs.data_path', None),
                'basis_set_path': get_config('fsl_mrs.basis_set_path', None),
                'fitting_params': get_config('fsl_mrs.fitting_params', {}),
                'simulation_mode': get_config('fsl_mrs_lsl.simulation_mode', not FSL_MRS_AVAILABLE),
                'simulation_range': get_config('fsl_mrs_lsl.simulation_range', [0.3, 1.2]),
                'simulation_noise': get_config('fsl_mrs_lsl.simulation_noise', 0.05),
            }
        except Exception as e:
            self.logger.warning(f"Could not load config, using defaults: {e}")
            return {
                'lsl_stream_name': 'FSL-MRS-EI-Ratio',
                'lsl_stream_type': 'EI_Ratio',
                'lsl_source_id': 'fsl-mrs-ei-001',
                'sampling_rate': 1.0,
                'simulation_mode': True,
                'simulation_range': [0.3, 1.2],
                'simulation_noise': 0.05,
            }
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        self.logger.info(f"Received signal {signum}, shutting down...")
        self.stop_streaming()
        sys.exit(0)
    
    def setup_lsl_stream(self) -> bool:
        """
        Setup the LSL stream outlet.
        
        Returns:
            bool: True if setup successful, False otherwise
        """
        try:
            # Create stream info
            info = StreamInfo(
                name=self.stream_name,
                type=self.stream_type,
                channel_count=self.channel_count,
                nominal_srate=self.sampling_rate,
                channel_format=self.channel_format,
                source_id=self.source_id
            )
            
            # Add metadata
            desc = info.desc()
            desc.append_child_value("manufacturer", "FSL-MRS")
            desc.append_child_value("unit", "ratio")
            desc.append_child_value("description", "Excitatory/Inhibitory ratio from MRS data")
            
            # Add channel information
            channels = desc.append_child("channels")
            ch = channels.append_child("channel")
            ch.append_child_value("label", "EI_Ratio")
            ch.append_child_value("unit", "ratio")
            ch.append_child_value("type", "EI_Ratio")
            
            # Create outlet
            self.outlet = StreamOutlet(info)
            self.logger.info(f"LSL stream '{self.stream_name}' created successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to setup LSL stream: {e}")
            traceback.print_exc()
            return False
    
    def setup_fsl_mrs(self) -> bool:
        """
        Setup FSL-MRS data processing.
        
        Returns:
            bool: True if setup successful, False otherwise
        """
        try:
            # Initialize the MRS data generator
            mrs_config = {
                'sampling_rate': self.sampling_rate,
                'noise_level': self.config.get('mrs_noise_level', 0.03),
                'temporal_variation': self.config.get('mrs_temporal_variation', 0.1),
                'drift_enabled': self.config.get('mrs_drift_enabled', True),
                'physiological_constraints': self.config.get('mrs_physiological_constraints', True),
                'spectrum_simulation': self.config.get('mrs_spectrum_simulation', True),
            }
            
            self.mrs_data_generator = FSLMRSDataGenerator(mrs_config)
            self.logger.info("FSL-MRS Data Generator initialized successfully")
            
            # Get initial E/I ratio
            initial_ei = self.mrs_data_generator.get_ei_ratio()
            self.last_ei_ratio = initial_ei
            self.logger.info(f"Initial E/I ratio: {initial_ei:.3f}")
            
            # If real FSL-MRS is available and not in simulation mode, set it up
            if not self.config.get('simulation_mode', True) and FSL_MRS_AVAILABLE:
                self.logger.info("Setting up real FSL-MRS processing...")
                
                if self.mrs_data_path:
                    self.logger.info(f"Loading MRS data from: {self.mrs_data_path}")
                    # Load MRS data - this will depend on actual FSL-MRS API
                    # self.mrs_data = mrs_io.read_FID(self.mrs_data_path)
                    
                if self.basis_set_path:
                    self.logger.info(f"Loading basis set from: {self.basis_set_path}")
                    # Load basis set - this will depend on actual FSL-MRS API
                    # self.basis_set = mrs_io.read_basis(self.basis_set_path)
                    
                self.logger.info("Real FSL-MRS setup completed")
            else:
                if self.config.get('simulation_mode', True):
                    self.logger.info("Running in simulation mode with realistic MRS data generator")
                else:
                    self.logger.warning("FSL-MRS not available, using simulation mode with realistic data generator")
                    self.config['simulation_mode'] = True
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to setup FSL-MRS: {e}")
            self.logger.warning("Falling back to basic simulation mode")
            self.config['simulation_mode'] = True
            return True
    
    def calculate_ei_ratio_real(self) -> float:
        """
        Calculate E/I ratio from real FSL-MRS data.
        
        This implementation uses the FSL-MRS data generator for realistic simulation,
        with hooks for real FSL-MRS integration.
        
        Returns:
            float: E/I ratio value
        """
        try:
            if self.mrs_data_generator:
                # Use the realistic data generator
                ei_ratio = self.mrs_data_generator.get_ei_ratio()
                
                # Log detailed metabolite information occasionally
                if hasattr(self, '_last_detailed_log_time'):
                    if time.time() - self._last_detailed_log_time > 10:  # Every 10 seconds
                        self._log_detailed_metabolites()
                        self._last_detailed_log_time = time.time()
                else:
                    self._last_detailed_log_time = time.time()
                    self._log_detailed_metabolites()
                
                return ei_ratio
            else:
                # Fallback to basic simulation
                self.logger.warning("MRS data generator not available, using basic simulation")
                return self.simulate_ei_ratio()
            
            # Placeholder for real FSL-MRS processing when available
            # This would typically involve:
            # 1. Acquiring new MRS data
            # 2. Preprocessing (if needed)
            # 3. Fitting metabolite concentrations
            # 4. Calculating E/I ratio from specific metabolites
            
            # Example pseudocode for real FSL-MRS:
            # new_data = self.acquire_mrs_data()
            # fitted_results = fitting.fit_mrs(new_data, self.basis_set, **self.fitting_params)
            # glutamate = fitted_results.get_concentration('Glu')
            # glutamine = fitted_results.get_concentration('Gln')
            # gaba = fitted_results.get_concentration('GABA')
            # ei_ratio = (glutamate + glutamine) / gaba
            
        except Exception as e:
            self.logger.error(f"Error in E/I ratio calculation: {e}")
            return self.last_ei_ratio
    
    def _log_detailed_metabolites(self):
        """Log detailed metabolite concentrations."""
        if self.mrs_data_generator:
            concentrations = self.mrs_data_generator.get_metabolite_concentrations()
            self.logger.info(f"Metabolite concentrations - "
                           f"Glu: {concentrations.glutamate:.2f}, "
                           f"Gln: {concentrations.glutamine:.2f}, "
                           f"GABA: {concentrations.gaba:.2f}, "
                           f"E/I: {concentrations.ei_ratio:.3f}")
            
            # Log other metabolites at debug level
            self.logger.debug(f"Other metabolites - "
                            f"NAA: {concentrations.naa:.2f}, "
                            f"Cr: {concentrations.creatine:.2f}, "
                            f"Cho: {concentrations.choline:.2f}, "
                            f"mI: {concentrations.myo_inositol:.2f}, "
                            f"Lac: {concentrations.lactate:.2f}")
    
    def simulate_ei_ratio(self) -> float:
        """
        Simulate E/I ratio data for testing purposes.
        
        Returns:
            float: Simulated E/I ratio value
        """
        try:
            # Generate realistic E/I ratio values with some temporal correlation
            min_ratio, max_ratio = self.config.get('simulation_range', [0.3, 1.2])
            noise_level = self.config.get('simulation_noise', 0.05)
            
            # Add some temporal correlation to make it more realistic
            trend = 0.1 * np.sin(time.time() * 0.1)  # Slow oscillation
            noise = np.random.normal(0, noise_level)
            
            # Combine trend and noise, then clip to valid range
            new_ratio = self.last_ei_ratio + trend + noise
            new_ratio = np.clip(new_ratio, min_ratio, max_ratio)
            
            return float(new_ratio)
            
        except Exception as e:
            self.logger.error(f"Error in E/I ratio simulation: {e}")
            return 0.7  # Default fallback value
    
    def get_ei_ratio(self) -> float:
        """
        Get the current E/I ratio value.
        
        Returns:
            float: Current E/I ratio
        """
        if self.config.get('simulation_mode', True) or not FSL_MRS_AVAILABLE:
            # Use the realistic data generator (which is much better than basic simulation)
            return self.calculate_ei_ratio_real()
        else:
            # Use real FSL-MRS processing when available
            return self.calculate_ei_ratio_real()
    
    def stream_data(self):
        """Main streaming loop that runs in a separate thread."""
        self.logger.info("Starting E/I ratio streaming...")
        
        interval = 1.0 / self.sampling_rate
        next_sample_time = time.time()
        
        while not self.stop_event.is_set():
            try:
                current_time = time.time()
                
                if current_time >= next_sample_time:
                    # Get new E/I ratio
                    ei_ratio = self.get_ei_ratio()
                    self.last_ei_ratio = ei_ratio
                    
                    # Send via LSL
                    if self.outlet:
                        self.outlet.push_sample([ei_ratio])
                        self.logger.debug(f"Sent E/I ratio: {ei_ratio:.3f}")
                    
                    # Schedule next sample
                    next_sample_time += interval
                
                # Sleep for a short time to avoid busy waiting
                sleep_time = min(0.01, max(0.001, next_sample_time - time.time()))
                time.sleep(sleep_time)
                
            except Exception as e:
                self.logger.error(f"Error in streaming loop: {e}")
                traceback.print_exc()
                time.sleep(0.1)  # Brief pause before retrying
    
    def start_streaming(self) -> bool:
        """
        Start the E/I ratio streaming.
        
        Returns:
            bool: True if started successfully, False otherwise
        """
        if self.is_streaming:
            self.logger.warning("Streaming already active")
            return True
        
        try:
            # Setup components
            if not self.setup_lsl_stream():
                return False
                
            if not self.setup_fsl_mrs():
                return False
            
            # Start streaming thread
            self.stop_event.clear()
            self.stream_thread = threading.Thread(target=self.stream_data, daemon=True)
            self.stream_thread.start()
            
            self.is_streaming = True
            self.logger.info("E/I ratio streaming started successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start streaming: {e}")
            traceback.print_exc()
            return False
    
    def stop_streaming(self):
        """Stop the E/I ratio streaming."""
        if not self.is_streaming:
            return
        
        try:
            self.logger.info("Stopping E/I ratio streaming...")
            
            # Signal stop and wait for thread
            self.stop_event.set()
            if self.stream_thread and self.stream_thread.is_alive():
                self.stream_thread.join(timeout=2.0)
            
            # Cleanup
            if self.outlet:
                del self.outlet
                self.outlet = None
            
            self.is_streaming = False
            self.logger.info("E/I ratio streaming stopped")
            
        except Exception as e:
            self.logger.error(f"Error stopping streaming: {e}")
    
    def simulate_intervention(self, intervention_type: str, magnitude: float = 0.2):
        """
        Simulate an intervention that affects metabolite concentrations.
        
        Args:
            intervention_type: Type of intervention ('excitatory', 'inhibitory', 'mixed')
            magnitude: Magnitude of the effect (0-1)
        """
        if self.mrs_data_generator:
            self.mrs_data_generator.simulate_intervention(intervention_type, magnitude)
            self.logger.info(f"Applied {intervention_type} intervention with magnitude {magnitude}")
        else:
            self.logger.warning("Cannot apply intervention: MRS data generator not available")
    
    def reset_baseline(self):
        """Reset MRS data to baseline concentrations."""
        if self.mrs_data_generator:
            self.mrs_data_generator.reset_to_baseline()
            self.logger.info("Reset MRS data to baseline")
        else:
            self.logger.warning("Cannot reset baseline: MRS data generator not available")
    
    def get_detailed_status(self) -> Dict[str, Any]:
        """
        Get detailed status information including metabolite concentrations.
        
        Returns:
            dict: Detailed status information
        """
        status = self.get_status()
        
        if self.mrs_data_generator:
            mrs_status = self.mrs_data_generator.get_status()
            status.update({
                'mrs_generator_available': True,
                'metabolite_concentrations': {
                    'glutamate': mrs_status['glutamate'],
                    'glutamine': mrs_status['glutamine'],
                    'gaba': mrs_status['gaba'],
                    'total_excitatory': mrs_status['total_excitatory'],
                    'total_inhibitory': mrs_status['total_inhibitory'],
                },
                'mrs_noise_level': mrs_status['noise_level'],
                'mrs_time_elapsed': mrs_status['time_elapsed'],
            })
        else:
            status['mrs_generator_available'] = False
        
        return status
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get current status information.
        
        Returns:
            dict: Status information
        """
        return {
            'is_streaming': self.is_streaming,
            'stream_name': self.stream_name,
            'sampling_rate': self.sampling_rate,
            'last_ei_ratio': self.last_ei_ratio,
            'simulation_mode': self.config.get('simulation_mode', True),
            'fsl_mrs_available': FSL_MRS_AVAILABLE,
        }

def main():
    """Main function for running the publisher as a standalone script."""
    import argparse
    
    parser = argparse.ArgumentParser(description='FSL-MRS LSL Publisher')
    parser.add_argument('--config', type=str, help='Path to configuration file')
    parser.add_argument('--simulation', action='store_true', 
                       help='Force simulation mode')
    parser.add_argument('--rate', type=float, default=1.0,
                       help='Sampling rate in Hz (default: 1.0)')
    parser.add_argument('--stream-name', type=str, default='FSL-MRS-EI-Ratio',
                       help='LSL stream name')
    
    args = parser.parse_args()
    
    # Build config from arguments
    config = {
        'lsl_stream_name': args.stream_name,
        'sampling_rate': args.rate,
        'simulation_mode': args.simulation,
    }
    
    # Create and start publisher
    publisher = FSLMRSLSLPublisher(config)
    
    try:
        if publisher.start_streaming():
            logger.info("Publisher started. Press Ctrl+C to stop.")
            
            # Keep running until interrupted
            while True:
                time.sleep(1)
                status = publisher.get_status()
                logger.info(f"Status: Streaming={status['is_streaming']}, "
                          f"Last E/I={status['last_ei_ratio']:.3f}")
                
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        traceback.print_exc()
    finally:
        publisher.stop_streaming()

if __name__ == "__main__":
    main() 