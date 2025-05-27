#!/usr/bin/env python3
"""
FSL-MRS Data Generator and Processor
Provides realistic MRS data simulation and E/I ratio calculation for testing,
with hooks for real FSL-MRS integration.
"""

import numpy as np
import time
import random
from typing import Dict, Any, Optional, Tuple, List
from dataclasses import dataclass, replace
from logger import get_logger

logger = get_logger("FSL_MRS_DataGen")

@dataclass
class MRSSpectrum:
    """Represents an MRS spectrum with metabolite concentrations."""
    frequency: np.ndarray
    intensity: np.ndarray
    metabolites: Dict[str, float]
    noise_level: float
    timestamp: float
    
@dataclass
class MetaboliteConcentrations:
    """Metabolite concentrations from MRS fitting."""
    glutamate: float  # Glu - excitatory
    glutamine: float  # Gln - excitatory precursor
    gaba: float       # GABA - inhibitory
    naa: float        # N-acetylaspartate - neuronal marker
    creatine: float   # Cr - energy metabolism
    choline: float    # Cho - membrane metabolism
    myo_inositol: float  # mI - glial marker
    lactate: float    # Lac - anaerobic metabolism
    
    @property
    def ei_ratio(self) -> float:
        """Calculate excitatory/inhibitory ratio."""
        excitatory = self.glutamate + self.glutamine
        inhibitory = self.gaba
        if inhibitory > 0:
            return excitatory / inhibitory
        else:
            logger.warning("GABA concentration is zero or negative, using default E/I ratio")
            return 1.0
    
    @property
    def total_excitatory(self) -> float:
        """Total excitatory neurotransmitter concentration."""
        return self.glutamate + self.glutamine
    
    @property
    def total_inhibitory(self) -> float:
        """Total inhibitory neurotransmitter concentration."""
        return self.gaba

class FSLMRSDataGenerator:
    """
    FSL-MRS Data Generator for realistic MRS data simulation.
    
    This class provides:
    1. Realistic MRS spectrum generation
    2. Metabolite concentration simulation with physiological constraints
    3. Temporal dynamics and noise modeling
    4. E/I ratio calculation
    5. Hooks for real FSL-MRS integration
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the FSL-MRS data generator.
        
        Args:
            config: Configuration dictionary with simulation parameters
        """
        self.config = config or self._load_default_config()
        self.logger = logger
        
        # Simulation parameters
        self.sampling_rate = self.config.get('sampling_rate', 1.0)
        self.noise_level = self.config.get('noise_level', 0.05)
        self.temporal_variation = self.config.get('temporal_variation', 0.1)
        
        # Physiological ranges for metabolites (in institutional units)
        self.metabolite_ranges = self.config.get('metabolite_ranges', {
            'glutamate': (8.0, 12.0),    # Glu: 8-12 IU
            'glutamine': (3.0, 6.0),     # Gln: 3-6 IU
            'gaba': (1.5, 3.0),          # GABA: 1.5-3 IU
            'naa': (7.0, 10.0),          # NAA: 7-10 IU
            'creatine': (6.0, 9.0),      # Cr: 6-9 IU
            'choline': (1.0, 2.5),       # Cho: 1-2.5 IU
            'myo_inositol': (3.0, 6.0),  # mI: 3-6 IU
            'lactate': (0.5, 2.0),       # Lac: 0.5-2 IU
        })
        
        # Frequency range for MRS spectrum (ppm)
        self.frequency_range = self.config.get('frequency_range', (0.5, 4.5))
        self.frequency_points = self.config.get('frequency_points', 2048)
        
        # Initialize baseline concentrations
        self.baseline_concentrations = self._generate_baseline_concentrations()
        self.current_concentrations = replace(self.baseline_concentrations)
        
        # Temporal dynamics
        self.time_start = time.time()
        self.drift_parameters = self._initialize_drift_parameters()
        
        self.logger.info("FSL-MRS Data Generator initialized")
        self.logger.info(f"Baseline E/I ratio: {self.baseline_concentrations.ei_ratio:.3f}")
        
    def _load_default_config(self) -> Dict[str, Any]:
        """Load default configuration."""
        return {
            'sampling_rate': 1.0,
            'noise_level': 0.05,
            'temporal_variation': 0.1,
            'drift_enabled': True,
            'physiological_constraints': True,
            'spectrum_simulation': True,
        }
    
    def _generate_baseline_concentrations(self) -> MetaboliteConcentrations:
        """Generate realistic baseline metabolite concentrations."""
        concentrations = {}
        
        for metabolite, (min_val, max_val) in self.metabolite_ranges.items():
            # Generate concentrations with slight bias toward middle of range
            mean_val = (min_val + max_val) / 2
            std_val = (max_val - min_val) / 6  # 99.7% within range
            concentration = np.clip(np.random.normal(mean_val, std_val), min_val, max_val)
            concentrations[metabolite] = concentration
        
        return MetaboliteConcentrations(**concentrations)
    
    def _initialize_drift_parameters(self) -> Dict[str, Dict[str, float]]:
        """Initialize parameters for temporal drift simulation."""
        drift_params = {}
        
        for metabolite in self.metabolite_ranges.keys():
            drift_params[metabolite] = {
                'frequency': np.random.uniform(0.001, 0.01),  # Very slow oscillations
                'amplitude': np.random.uniform(0.02, 0.08),   # 2-8% variation
                'phase': np.random.uniform(0, 2 * np.pi),     # Random phase
                'trend': np.random.uniform(-0.001, 0.001),    # Slow linear trend
            }
        
        return drift_params
    
    def _apply_temporal_dynamics(self, baseline: MetaboliteConcentrations, 
                                current_time: float) -> MetaboliteConcentrations:
        """Apply temporal dynamics to metabolite concentrations."""
        if not self.config.get('drift_enabled', True):
            return baseline
        
        elapsed_time = current_time - self.time_start
        new_concentrations = {}
        
        for metabolite in self.metabolite_ranges.keys():
            baseline_val = getattr(baseline, metabolite)
            params = self.drift_parameters[metabolite]
            
            # Sinusoidal variation
            oscillation = params['amplitude'] * np.sin(
                2 * np.pi * params['frequency'] * elapsed_time + params['phase']
            )
            
            # Linear trend
            trend = params['trend'] * elapsed_time
            
            # Random noise
            noise = np.random.normal(0, self.noise_level * baseline_val)
            
            # Apply changes
            new_val = baseline_val * (1 + oscillation + trend) + noise
            
            # Apply physiological constraints
            if self.config.get('physiological_constraints', True):
                min_val, max_val = self.metabolite_ranges[metabolite]
                new_val = np.clip(new_val, min_val, max_val)
            
            new_concentrations[metabolite] = new_val
        
        return MetaboliteConcentrations(**new_concentrations)
    
    def _generate_spectrum(self, concentrations: MetaboliteConcentrations) -> MRSSpectrum:
        """Generate a realistic MRS spectrum from metabolite concentrations."""
        # Create frequency axis
        freq_min, freq_max = self.frequency_range
        frequency = np.linspace(freq_min, freq_max, self.frequency_points)
        
        # Initialize spectrum
        intensity = np.zeros_like(frequency)
        
        # Metabolite peak parameters (chemical shift in ppm, relative intensity)
        peak_params = {
            'naa': [(2.02, 1.0), (2.6, 0.3)],  # NAA has multiple peaks
            'creatine': [(3.03, 1.0), (3.9, 0.8)],  # Cr and PCr
            'choline': [(3.2, 1.0)],
            'myo_inositol': [(3.56, 1.0), (4.06, 0.6)],
            'glutamate': [(2.35, 0.8), (3.75, 0.4)],
            'glutamine': [(2.45, 0.6), (3.77, 0.3)],
            'gaba': [(2.28, 0.5), (3.01, 0.3)],
            'lactate': [(1.33, 1.0), (4.1, 0.2)],
        }
        
        # Add metabolite peaks
        for metabolite, peaks in peak_params.items():
            concentration = getattr(concentrations, metabolite)
            for chemical_shift, relative_intensity in peaks:
                if freq_min <= chemical_shift <= freq_max:
                    # Gaussian peak
                    peak_width = 0.05  # Peak width in ppm
                    peak_intensity = concentration * relative_intensity
                    gaussian = peak_intensity * np.exp(
                        -0.5 * ((frequency - chemical_shift) / peak_width) ** 2
                    )
                    intensity += gaussian
        
        # Add baseline and noise
        baseline_level = np.random.uniform(0.1, 0.3)
        noise = np.random.normal(0, self.noise_level * np.max(intensity), len(frequency))
        intensity += baseline_level + noise
        
        return MRSSpectrum(
            frequency=frequency,
            intensity=intensity,
            metabolites={name: getattr(concentrations, name) for name in self.metabolite_ranges.keys()},
            noise_level=self.noise_level,
            timestamp=time.time()
        )
    
    def acquire_mrs_data(self) -> Tuple[MetaboliteConcentrations, Optional[MRSSpectrum]]:
        """
        Acquire new MRS data (simulated or real).
        
        Returns:
            Tuple of (metabolite_concentrations, spectrum)
        """
        current_time = time.time()
        
        # Apply temporal dynamics
        self.current_concentrations = self._apply_temporal_dynamics(
            self.baseline_concentrations, current_time
        )
        
        # Generate spectrum if enabled
        spectrum = None
        if self.config.get('spectrum_simulation', True):
            spectrum = self._generate_spectrum(self.current_concentrations)
        
        self.logger.debug(f"Generated MRS data - E/I ratio: {self.current_concentrations.ei_ratio:.3f}")
        
        return self.current_concentrations, spectrum
    
    def get_ei_ratio(self) -> float:
        """Get the current E/I ratio."""
        concentrations, _ = self.acquire_mrs_data()
        return concentrations.ei_ratio
    
    def get_metabolite_concentrations(self) -> MetaboliteConcentrations:
        """Get current metabolite concentrations."""
        concentrations, _ = self.acquire_mrs_data()
        return concentrations
    
    def get_full_spectrum(self) -> MRSSpectrum:
        """Get the full MRS spectrum."""
        concentrations, spectrum = self.acquire_mrs_data()
        if spectrum is None:
            # Generate spectrum if not already done
            spectrum = self._generate_spectrum(concentrations)
        return spectrum
    
    def simulate_intervention(self, intervention_type: str, magnitude: float = 0.2):
        """
        Simulate an intervention that affects metabolite concentrations.
        
        Args:
            intervention_type: Type of intervention ('excitatory', 'inhibitory', 'mixed')
            magnitude: Magnitude of the effect (0-1)
        """
        self.logger.info(f"Simulating {intervention_type} intervention with magnitude {magnitude}")
        
        if intervention_type == 'excitatory':
            # Increase glutamate/glutamine, slight decrease in GABA
            self.baseline_concentrations.glutamate *= (1 + magnitude)
            self.baseline_concentrations.glutamine *= (1 + magnitude * 0.5)
            self.baseline_concentrations.gaba *= (1 - magnitude * 0.2)
            
        elif intervention_type == 'inhibitory':
            # Increase GABA, slight decrease in glutamate
            self.baseline_concentrations.gaba *= (1 + magnitude)
            self.baseline_concentrations.glutamate *= (1 - magnitude * 0.3)
            
        elif intervention_type == 'mixed':
            # Random changes to simulate complex interventions
            for metabolite in ['glutamate', 'glutamine', 'gaba']:
                change = np.random.uniform(-magnitude, magnitude)
                current_val = getattr(self.baseline_concentrations, metabolite)
                new_val = current_val * (1 + change)
                
                # Apply constraints
                min_val, max_val = self.metabolite_ranges[metabolite]
                new_val = np.clip(new_val, min_val, max_val)
                setattr(self.baseline_concentrations, metabolite, new_val)
        
        # Apply physiological constraints
        for metabolite in self.metabolite_ranges.keys():
            min_val, max_val = self.metabolite_ranges[metabolite]
            current_val = getattr(self.baseline_concentrations, metabolite)
            constrained_val = np.clip(current_val, min_val, max_val)
            setattr(self.baseline_concentrations, metabolite, constrained_val)
        
        self.logger.info(f"New baseline E/I ratio: {self.baseline_concentrations.ei_ratio:.3f}")
    
    def reset_to_baseline(self):
        """Reset concentrations to original baseline."""
        self.baseline_concentrations = self._generate_baseline_concentrations()
        self.time_start = time.time()
        self.drift_parameters = self._initialize_drift_parameters()
        self.logger.info("Reset to new baseline concentrations")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current status information."""
        concentrations = self.current_concentrations
        return {
            'ei_ratio': concentrations.ei_ratio,
            'glutamate': concentrations.glutamate,
            'glutamine': concentrations.glutamine,
            'gaba': concentrations.gaba,
            'total_excitatory': concentrations.total_excitatory,
            'total_inhibitory': concentrations.total_inhibitory,
            'noise_level': self.noise_level,
            'temporal_variation': self.temporal_variation,
            'time_elapsed': time.time() - self.time_start,
        }

def main():
    """Test the FSL-MRS data generator."""
    print("Testing FSL-MRS Data Generator...")
    
    # Create generator
    config = {
        'sampling_rate': 2.0,
        'noise_level': 0.03,
        'temporal_variation': 0.15,
        'drift_enabled': True,
    }
    
    generator = FSLMRSDataGenerator(config)
    
    print(f"Initial E/I ratio: {generator.baseline_concentrations.ei_ratio:.3f}")
    print(f"Initial Glu: {generator.baseline_concentrations.glutamate:.2f}")
    print(f"Initial GABA: {generator.baseline_concentrations.gaba:.2f}")
    print()
    
    # Test data acquisition
    print("Testing data acquisition...")
    for i in range(5):
        concentrations, spectrum = generator.acquire_mrs_data()
        print(f"Sample {i+1}: E/I = {concentrations.ei_ratio:.3f}, "
              f"Glu = {concentrations.glutamate:.2f}, "
              f"GABA = {concentrations.gaba:.2f}")
        time.sleep(0.5)
    
    print()
    
    # Test intervention
    print("Testing excitatory intervention...")
    generator.simulate_intervention('excitatory', 0.3)
    
    for i in range(3):
        concentrations, _ = generator.acquire_mrs_data()
        print(f"Post-intervention {i+1}: E/I = {concentrations.ei_ratio:.3f}")
        time.sleep(0.5)
    
    print()
    print("FSL-MRS Data Generator test completed!")

if __name__ == "__main__":
    main() 