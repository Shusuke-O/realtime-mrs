#!/usr/bin/env python3
"""
MRS Sequence Analysis Framework for Real-time Neurofeedback
Research: Managing Plasticity and Stability in Skill Learning by Manipulating E/I Ratio
Author: Shusuke Okita
Institution: RIKEN CBS

This module provides comprehensive analysis tools for comparing MRS sequences
(STEAM vs semi-LASER) to determine optimal parameters for real-time neurofeedback.

Key Analysis Areas:
1. Temporal resolution assessment
2. Signal stability and SNR analysis
3. GABA/Glutamate quantification accuracy
4. Real-time processing feasibility
5. Sequence parameter optimization
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import signal, stats
from scipy.optimize import curve_fit
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
import warnings
from typing import Dict, List, Tuple, Optional, Union
from dataclasses import dataclass
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.preprocessing import StandardScaler
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Set plotting style
plt.style.use('seaborn-v0_8')
sns.set_palette("husl")

@dataclass
class MRSSequenceParams:
    """Parameters for MRS sequences"""
    name: str
    tr: float  # Repetition time (seconds)
    te: float  # Echo time (milliseconds)
    voxel_size: Tuple[float, float, float]  # cm^3
    phase_cycling: int  # Number of phase cycles
    sar_limit: float  # SAR limitation factor
    signal_efficiency: float  # Relative signal efficiency
    
    @property
    def temporal_resolution(self) -> float:
        """Effective temporal resolution considering phase cycling"""
        return self.tr * self.phase_cycling
    
    @property
    def theoretical_snr(self) -> float:
        """Theoretical SNR relative to baseline"""
        return self.signal_efficiency / np.sqrt(self.temporal_resolution)

@dataclass
class MRSData:
    """Container for MRS measurement data"""
    timestamps: np.ndarray
    gaba_concentration: np.ndarray
    glutamate_concentration: np.ndarray
    glutamine_concentration: np.ndarray
    sequence_params: MRSSequenceParams
    metadata: Dict
    
    @property
    def ei_ratio(self) -> np.ndarray:
        """Calculate E/I ratio: (Glu + Gln) / GABA"""
        return (self.glutamate_concentration + self.glutamine_concentration) / self.gaba_concentration
    
    @property
    def duration_minutes(self) -> float:
        """Total measurement duration in minutes"""
        return (self.timestamps[-1] - self.timestamps[0]) / 60.0

class MRSSequenceAnalyzer:
    """
    Comprehensive analyzer for MRS sequence comparison and optimization
    """
    
    def __init__(self):
        self.sequences = self._initialize_sequences()
        self.analysis_results = {}
        
    def _initialize_sequences(self) -> Dict[str, MRSSequenceParams]:
        """Initialize standard MRS sequence parameters"""
        sequences = {
            'STEAM': MRSSequenceParams(
                name='STEAM',
                tr=3.5,  # 3-4s range
                te=7.0,  # milliseconds
                voxel_size=(2.0, 2.0, 2.0),  # cm^3
                phase_cycling=2,  # Minimum for artifact reduction
                sar_limit=0.3,  # Low SAR
                signal_efficiency=0.5  # Half signal compared to semi-LASER
            ),
            'semi-LASER': MRSSequenceParams(
                name='semi-LASER',
                tr=6.5,  # 6-7s range (SAR limited)
                te=30.0,  # milliseconds
                voxel_size=(2.0, 2.0, 2.0),  # cm^3
                phase_cycling=2,  # Minimum for artifact reduction
                sar_limit=0.8,  # Higher SAR
                signal_efficiency=1.0  # Reference signal level
            )
        }
        return sequences
    
    def simulate_mrs_measurement(self, sequence_name: str, duration_minutes: float = 10,
                                task_periods: Optional[List[Tuple[float, float]]] = None) -> MRSData:
        """
        Simulate MRS measurement data for sequence evaluation
        
        Args:
            sequence_name: 'STEAM' or 'semi-LASER'
            duration_minutes: Total measurement duration
            task_periods: List of (start, end) times for task periods in minutes
            
        Returns:
            MRSData object with simulated measurements
        """
        sequence = self.sequences[sequence_name]
        
        # Generate timestamps
        n_measurements = int(duration_minutes * 60 / sequence.temporal_resolution)
        timestamps = np.arange(n_measurements) * sequence.temporal_resolution
        
        # Baseline concentrations (institutional units)
        baseline_gaba = 2.0
        baseline_glu = 10.0
        baseline_gln = 4.0
        
        # Simulate physiological variations
        np.random.seed(42)  # For reproducible simulations
        
        # Generate realistic concentration time series
        gaba_conc = self._simulate_concentration_timeseries(
            timestamps, baseline_gaba, sequence, task_periods, metabolite='GABA'
        )
        glu_conc = self._simulate_concentration_timeseries(
            timestamps, baseline_glu, sequence, task_periods, metabolite='Glutamate'
        )
        gln_conc = self._simulate_concentration_timeseries(
            timestamps, baseline_gln, sequence, task_periods, metabolite='Glutamine'
        )
        
        metadata = {
            'simulation_date': datetime.now().isoformat(),
            'sequence_name': sequence_name,
            'duration_minutes': duration_minutes,
            'n_measurements': n_measurements,
            'task_periods': task_periods
        }
        
        return MRSData(
            timestamps=timestamps,
            gaba_concentration=gaba_conc,
            glutamate_concentration=glu_conc,
            glutamine_concentration=gln_conc,
            sequence_params=sequence,
            metadata=metadata
        )
    
    def _simulate_concentration_timeseries(self, timestamps: np.ndarray, baseline: float,
                                         sequence: MRSSequenceParams, task_periods: Optional[List],
                                         metabolite: str) -> np.ndarray:
        """Simulate realistic metabolite concentration time series"""
        
        # Base signal
        concentrations = np.full_like(timestamps, baseline)
        
        # Add slow drift (scanner instability)
        drift_amplitude = baseline * 0.02  # 2% drift
        drift_period = len(timestamps) * 0.8  # Slow drift
        drift = drift_amplitude * np.sin(2 * np.pi * np.arange(len(timestamps)) / drift_period)
        concentrations += drift
        
        # Add task-related changes if task periods specified
        if task_periods:
            for start_min, end_min in task_periods:
                start_idx = int(start_min * 60 / sequence.temporal_resolution)
                end_idx = int(end_min * 60 / sequence.temporal_resolution)
                
                if metabolite == 'GABA':
                    # GABA decreases during task, then recovers
                    task_effect = -0.15 * baseline  # 15% decrease
                    recovery_tau = 300  # 5 minutes recovery time constant
                elif metabolite == 'Glutamate':
                    # Glutamate increases during task
                    task_effect = 0.20 * baseline  # 20% increase
                    recovery_tau = 180  # 3 minutes recovery
                else:  # Glutamine
                    # Glutamine shows delayed increase
                    task_effect = 0.10 * baseline  # 10% increase
                    recovery_tau = 240  # 4 minutes recovery
                
                # Apply task effect with exponential recovery
                for i in range(start_idx, min(end_idx, len(concentrations))):
                    concentrations[i] += task_effect
                
                # Exponential recovery after task
                for i in range(end_idx, len(concentrations)):
                    time_since_end = (i - end_idx) * sequence.temporal_resolution
                    recovery_factor = np.exp(-time_since_end / recovery_tau)
                    concentrations[i] += task_effect * recovery_factor
        
        # Add measurement noise based on sequence SNR
        noise_std = baseline * (0.05 / sequence.theoretical_snr)  # SNR-dependent noise
        noise = np.random.normal(0, noise_std, len(concentrations))
        concentrations += noise
        
        # Add sequence-specific artifacts
        if sequence.name == 'STEAM':
            # STEAM has lower signal but less artifacts
            artifact_amplitude = baseline * 0.02
        else:  # semi-LASER
            # semi-LASER has higher signal but more SAR-related artifacts
            artifact_amplitude = baseline * 0.03
        
        # Random artifacts (shimming issues, motion, etc.)
        n_artifacts = np.random.poisson(len(concentrations) * 0.01)  # 1% of measurements
        artifact_indices = np.random.choice(len(concentrations), n_artifacts, replace=False)
        for idx in artifact_indices:
            concentrations[idx] += np.random.normal(0, artifact_amplitude)
        
        return np.maximum(concentrations, 0.1 * baseline)  # Ensure positive concentrations
    
    def analyze_temporal_resolution(self, data_list: List[MRSData]) -> Dict:
        """
        Analyze temporal resolution characteristics of different sequences
        
        Args:
            data_list: List of MRSData objects from different sequences
            
        Returns:
            Dictionary with temporal resolution analysis results
        """
        logger.info("Analyzing temporal resolution characteristics...")
        
        results = {}
        
        for data in data_list:
            seq_name = data.sequence_params.name
            
            # Calculate effective sampling rate
            sampling_intervals = np.diff(data.timestamps)
            effective_sampling_rate = 1.0 / np.mean(sampling_intervals)
            
            # Assess ability to detect rapid changes
            ei_ratio = data.ei_ratio
            ei_diff = np.diff(ei_ratio)
            
            # Calculate temporal sensitivity (ability to detect changes)
            temporal_sensitivity = np.std(ei_diff) / np.mean(ei_ratio)
            
            # Nyquist frequency for detectable oscillations
            nyquist_freq = effective_sampling_rate / 2
            
            results[seq_name] = {
                'effective_sampling_rate': effective_sampling_rate,
                'temporal_resolution_seconds': data.sequence_params.temporal_resolution,
                'temporal_sensitivity': temporal_sensitivity,
                'nyquist_frequency': nyquist_freq,
                'max_detectable_period_minutes': (1 / nyquist_freq) / 60,
                'n_measurements': len(data.timestamps),
                'measurement_duration_minutes': data.duration_minutes
            }
        
        return results
    
    def analyze_signal_stability(self, data_list: List[MRSData]) -> Dict:
        """
        Analyze signal stability and noise characteristics
        
        Args:
            data_list: List of MRSData objects
            
        Returns:
            Dictionary with stability analysis results
        """
        logger.info("Analyzing signal stability and noise characteristics...")
        
        results = {}
        
        for data in data_list:
            seq_name = data.sequence_params.name
            
            # Calculate stability metrics for each metabolite
            metabolites = {
                'GABA': data.gaba_concentration,
                'Glutamate': data.glutamate_concentration,
                'Glutamine': data.glutamine_concentration,
                'EI_Ratio': data.ei_ratio
            }
            
            stability_metrics = {}
            
            for met_name, concentrations in metabolites.items():
                # Coefficient of variation
                cv = np.std(concentrations) / np.mean(concentrations)
                
                # Signal-to-noise ratio estimate
                # Use moving window to estimate signal vs noise
                window_size = min(10, len(concentrations) // 4)
                smoothed = signal.savgol_filter(concentrations, window_size, 3)
                noise = concentrations - smoothed
                snr = np.mean(smoothed) / np.std(noise)
                
                # Drift analysis (linear trend)
                time_minutes = data.timestamps / 60
                slope, intercept, r_value, p_value, std_err = stats.linregress(time_minutes, concentrations)
                drift_percent_per_minute = (slope / np.mean(concentrations)) * 100
                
                # Stability over time (using Allan variance)
                allan_var = self._calculate_allan_variance(concentrations)
                
                stability_metrics[met_name] = {
                    'coefficient_of_variation': cv,
                    'snr_estimate': snr,
                    'drift_percent_per_minute': drift_percent_per_minute,
                    'drift_p_value': p_value,
                    'allan_variance': allan_var,
                    'mean_concentration': np.mean(concentrations),
                    'std_concentration': np.std(concentrations)
                }
            
            results[seq_name] = {
                'sequence_params': data.sequence_params.__dict__,
                'stability_metrics': stability_metrics,
                'overall_stability_score': self._calculate_stability_score(stability_metrics)
            }
        
        return results
    
    def _calculate_allan_variance(self, data: np.ndarray, max_tau: Optional[int] = None) -> Dict:
        """Calculate Allan variance for stability analysis"""
        if max_tau is None:
            max_tau = len(data) // 4
        
        taus = np.logspace(0, np.log10(max_tau), 20).astype(int)
        taus = np.unique(taus)
        
        allan_vars = []
        for tau in taus:
            if tau >= len(data) - 1:
                break
            
            # Calculate Allan variance for this tau
            n_groups = len(data) // tau
            if n_groups < 2:
                break
            
            grouped_means = []
            for i in range(n_groups):
                start_idx = i * tau
                end_idx = (i + 1) * tau
                grouped_means.append(np.mean(data[start_idx:end_idx]))
            
            if len(grouped_means) >= 2:
                allan_var = np.var(np.diff(grouped_means)) / 2
                allan_vars.append(allan_var)
            else:
                break
        
        return {
            'taus': taus[:len(allan_vars)].tolist(),
            'allan_variances': allan_vars,
            'min_allan_variance': min(allan_vars) if allan_vars else np.nan,
            'optimal_averaging_time': taus[np.argmin(allan_vars)] if allan_vars else np.nan
        }
    
    def _calculate_stability_score(self, stability_metrics: Dict) -> float:
        """Calculate overall stability score (0-100, higher is better)"""
        scores = []
        
        for met_name, metrics in stability_metrics.items():
            # Lower CV is better
            cv_score = max(0, 100 - metrics['coefficient_of_variation'] * 1000)
            
            # Higher SNR is better
            snr_score = min(100, metrics['snr_estimate'] * 10)
            
            # Lower drift is better
            drift_score = max(0, 100 - abs(metrics['drift_percent_per_minute']) * 10)
            
            met_score = (cv_score + snr_score + drift_score) / 3
            scores.append(met_score)
        
        return np.mean(scores)
    
    def analyze_quantification_accuracy(self, data_list: List[MRSData]) -> Dict:
        """
        Analyze quantification accuracy for GABA and Glutamate
        
        Args:
            data_list: List of MRSData objects
            
        Returns:
            Dictionary with quantification accuracy results
        """
        logger.info("Analyzing metabolite quantification accuracy...")
        
        results = {}
        
        for data in data_list:
            seq_name = data.sequence_params.name
            
            # Known ground truth from simulation
            true_baseline_gaba = 2.0
            true_baseline_glu = 10.0
            true_baseline_gln = 4.0
            
            # Calculate accuracy metrics
            gaba_accuracy = self._calculate_accuracy_metrics(
                data.gaba_concentration, true_baseline_gaba
            )
            glu_accuracy = self._calculate_accuracy_metrics(
                data.glutamate_concentration, true_baseline_glu
            )
            gln_accuracy = self._calculate_accuracy_metrics(
                data.glutamine_concentration, true_baseline_gln
            )
            
            # E/I ratio accuracy
            true_ei_ratio = (true_baseline_glu + true_baseline_gln) / true_baseline_gaba
            ei_accuracy = self._calculate_accuracy_metrics(
                data.ei_ratio, true_ei_ratio
            )
            
            results[seq_name] = {
                'GABA_accuracy': gaba_accuracy,
                'Glutamate_accuracy': glu_accuracy,
                'Glutamine_accuracy': gln_accuracy,
                'EI_ratio_accuracy': ei_accuracy,
                'overall_accuracy_score': np.mean([
                    gaba_accuracy['accuracy_score'],
                    glu_accuracy['accuracy_score'],
                    gln_accuracy['accuracy_score'],
                    ei_accuracy['accuracy_score']
                ])
            }
        
        return results
    
    def _calculate_accuracy_metrics(self, measured: np.ndarray, true_value: float) -> Dict:
        """Calculate accuracy metrics for a metabolite"""
        
        # Bias (systematic error)
        bias = np.mean(measured) - true_value
        bias_percent = (bias / true_value) * 100
        
        # Precision (random error)
        precision = np.std(measured)
        precision_percent = (precision / true_value) * 100
        
        # Root mean square error
        rmse = np.sqrt(np.mean((measured - true_value) ** 2))
        rmse_percent = (rmse / true_value) * 100
        
        # Accuracy score (0-100, higher is better)
        accuracy_score = max(0, 100 - rmse_percent)
        
        return {
            'bias': bias,
            'bias_percent': bias_percent,
            'precision': precision,
            'precision_percent': precision_percent,
            'rmse': rmse,
            'rmse_percent': rmse_percent,
            'accuracy_score': accuracy_score,
            'mean_measured': np.mean(measured),
            'true_value': true_value
        }
    
    def analyze_realtime_feasibility(self, data_list: List[MRSData]) -> Dict:
        """
        Analyze real-time processing feasibility
        
        Args:
            data_list: List of MRSData objects
            
        Returns:
            Dictionary with real-time feasibility analysis
        """
        logger.info("Analyzing real-time processing feasibility...")
        
        results = {}
        
        for data in data_list:
            seq_name = data.sequence_params.name
            
            # Processing time requirements
            temporal_res = data.sequence_params.temporal_resolution
            
            # Estimate processing time (based on typical FSL-MRS processing)
            # This would need to be measured empirically
            estimated_processing_time = {
                'STEAM': temporal_res * 0.3,  # 30% of TR
                'semi-LASER': temporal_res * 0.4  # 40% of TR (more complex)
            }[seq_name]
            
            # Real-time feasibility score
            processing_margin = temporal_res - estimated_processing_time
            feasibility_score = min(100, (processing_margin / temporal_res) * 100)
            
            # Latency analysis
            total_latency = estimated_processing_time + 0.5  # Add network/system delays
            
            # Feedback effectiveness (based on neurofeedback literature)
            # Optimal feedback latency < 2 seconds for effective learning
            feedback_effectiveness = max(0, 100 - (total_latency / 2.0) * 100)
            
            results[seq_name] = {
                'temporal_resolution': temporal_res,
                'estimated_processing_time': estimated_processing_time,
                'processing_margin': processing_margin,
                'total_latency': total_latency,
                'feasibility_score': feasibility_score,
                'feedback_effectiveness': feedback_effectiveness,
                'realtime_capable': processing_margin > 0,
                'optimal_for_feedback': total_latency < 2.0
            }
        
        return results
    
    def optimize_sequence_parameters(self, sequence_name: str, 
                                   optimization_target: str = 'balanced') -> Dict:
        """
        Optimize sequence parameters for specific targets
        
        Args:
            sequence_name: 'STEAM' or 'semi-LASER'
            optimization_target: 'temporal_resolution', 'snr', 'balanced'
            
        Returns:
            Dictionary with optimized parameters
        """
        logger.info(f"Optimizing {sequence_name} parameters for {optimization_target}...")
        
        base_sequence = self.sequences[sequence_name]
        
        # Define parameter ranges for optimization
        if sequence_name == 'STEAM':
            tr_range = np.arange(3.0, 5.0, 0.5)
            phase_cycling_range = [2, 4, 8]
        else:  # semi-LASER
            tr_range = np.arange(5.0, 8.0, 0.5)
            phase_cycling_range = [2, 4, 8]
        
        best_params = None
        best_score = -np.inf
        optimization_results = []
        
        for tr in tr_range:
            for phase_cycles in phase_cycling_range:
                # Create test sequence
                test_sequence = MRSSequenceParams(
                    name=sequence_name,
                    tr=tr,
                    te=base_sequence.te,
                    voxel_size=base_sequence.voxel_size,
                    phase_cycling=phase_cycles,
                    sar_limit=base_sequence.sar_limit,
                    signal_efficiency=base_sequence.signal_efficiency
                )
                
                # Calculate optimization score
                score = self._calculate_optimization_score(test_sequence, optimization_target)
                
                optimization_results.append({
                    'tr': tr,
                    'phase_cycling': phase_cycles,
                    'temporal_resolution': test_sequence.temporal_resolution,
                    'theoretical_snr': test_sequence.theoretical_snr,
                    'score': score
                })
                
                if score > best_score:
                    best_score = score
                    best_params = test_sequence
        
        return {
            'optimized_sequence': best_params,
            'optimization_score': best_score,
            'optimization_target': optimization_target,
            'parameter_sweep_results': optimization_results
        }
    
    def _calculate_optimization_score(self, sequence: MRSSequenceParams, target: str) -> float:
        """Calculate optimization score for given target"""
        
        if target == 'temporal_resolution':
            # Prioritize fast temporal resolution
            return 100 / sequence.temporal_resolution
        
        elif target == 'snr':
            # Prioritize high SNR
            return sequence.theoretical_snr * 100
        
        elif target == 'balanced':
            # Balance temporal resolution and SNR
            temporal_score = 100 / sequence.temporal_resolution
            snr_score = sequence.theoretical_snr * 100
            
            # Real-time feasibility bonus
            realtime_bonus = 50 if sequence.temporal_resolution <= 10 else 0
            
            return (temporal_score + snr_score + realtime_bonus) / 3
        
        else:
            raise ValueError(f"Unknown optimization target: {target}")
    
    def generate_comparison_report(self, steam_data: MRSData, semi_laser_data: MRSData) -> Dict:
        """
        Generate comprehensive comparison report between STEAM and semi-LASER
        
        Args:
            steam_data: MRSData from STEAM sequence
            semi_laser_data: MRSData from semi-LASER sequence
            
        Returns:
            Comprehensive comparison report
        """
        logger.info("Generating comprehensive sequence comparison report...")
        
        data_list = [steam_data, semi_laser_data]
        
        # Run all analyses
        temporal_analysis = self.analyze_temporal_resolution(data_list)
        stability_analysis = self.analyze_signal_stability(data_list)
        accuracy_analysis = self.analyze_quantification_accuracy(data_list)
        realtime_analysis = self.analyze_realtime_feasibility(data_list)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(
            temporal_analysis, stability_analysis, accuracy_analysis, realtime_analysis
        )
        
        report = {
            'analysis_timestamp': datetime.now().isoformat(),
            'sequences_compared': ['STEAM', 'semi-LASER'],
            'temporal_resolution_analysis': temporal_analysis,
            'signal_stability_analysis': stability_analysis,
            'quantification_accuracy_analysis': accuracy_analysis,
            'realtime_feasibility_analysis': realtime_analysis,
            'recommendations': recommendations,
            'summary_scores': self._calculate_summary_scores(
                stability_analysis, accuracy_analysis, realtime_analysis
            )
        }
        
        return report
    
    def _generate_recommendations(self, temporal_analysis: Dict, stability_analysis: Dict,
                                accuracy_analysis: Dict, realtime_analysis: Dict) -> Dict:
        """Generate recommendations based on analysis results"""
        
        recommendations = {
            'primary_recommendation': '',
            'rationale': '',
            'alternative_scenarios': {},
            'parameter_suggestions': {},
            'implementation_considerations': []
        }
        
        # Extract key metrics
        steam_temporal = temporal_analysis['STEAM']['temporal_resolution_seconds']
        laser_temporal = temporal_analysis['semi-LASER']['temporal_resolution_seconds']
        
        steam_stability = stability_analysis['STEAM']['overall_stability_score']
        laser_stability = stability_analysis['semi-LASER']['overall_stability_score']
        
        steam_accuracy = accuracy_analysis['STEAM']['overall_accuracy_score']
        laser_accuracy = accuracy_analysis['semi-LASER']['overall_accuracy_score']
        
        steam_realtime = realtime_analysis['STEAM']['feasibility_score']
        laser_realtime = realtime_analysis['semi-LASER']['feasibility_score']
        
        # Decision logic
        if steam_temporal < 8 and steam_realtime > 70:
            recommendations['primary_recommendation'] = 'STEAM'
            recommendations['rationale'] = (
                f"STEAM provides superior temporal resolution ({steam_temporal:.1f}s vs "
                f"{laser_temporal:.1f}s) with good real-time feasibility (score: {steam_realtime:.1f}). "
                f"This is critical for effective neurofeedback applications."
            )
        elif laser_stability > steam_stability + 10 and laser_accuracy > steam_accuracy + 10:
            recommendations['primary_recommendation'] = 'semi-LASER'
            recommendations['rationale'] = (
                f"semi-LASER provides superior signal stability (score: {laser_stability:.1f} vs "
                f"{steam_stability:.1f}) and accuracy (score: {laser_accuracy:.1f} vs "
                f"{steam_accuracy:.1f}), which may be more important for reliable measurements."
            )
        else:
            recommendations['primary_recommendation'] = 'STEAM'
            recommendations['rationale'] = (
                "STEAM is recommended for real-time neurofeedback applications due to better "
                "temporal resolution and lower SAR limitations, despite some trade-offs in SNR."
            )
        
        # Alternative scenarios
        recommendations['alternative_scenarios'] = {
            'high_precision_required': 'semi-LASER for maximum accuracy and stability',
            'rapid_feedback_critical': 'STEAM with optimized parameters',
            'long_duration_studies': 'STEAM due to lower SAR limitations',
            'research_validation': 'Both sequences for comprehensive comparison'
        }
        
        # Parameter suggestions
        recommendations['parameter_suggestions'] = {
            'STEAM': {
                'tr': '3.5s (balance of speed and SNR)',
                'phase_cycling': '2 (minimum for artifact reduction)',
                'optimization_focus': 'temporal resolution'
            },
            'semi-LASER': {
                'tr': '6.0s (if SAR permits)',
                'phase_cycling': '4 (improved stability)',
                'optimization_focus': 'signal quality'
            }
        }
        
        # Implementation considerations
        recommendations['implementation_considerations'] = [
            "Validate real-time processing pipeline with chosen sequence",
            "Conduct pilot studies to confirm SNR and stability in target regions",
            "Test phase cycling optimization for artifact reduction",
            "Implement quality control metrics for real-time monitoring",
            "Consider adaptive parameter adjustment based on individual SNR",
            "Plan for SAR monitoring and cooling periods if using semi-LASER"
        ]
        
        return recommendations
    
    def _calculate_summary_scores(self, stability_analysis: Dict, accuracy_analysis: Dict,
                                realtime_analysis: Dict) -> Dict:
        """Calculate summary scores for easy comparison"""
        
        summary = {}
        
        for seq_name in ['STEAM', 'semi-LASER']:
            stability_score = stability_analysis[seq_name]['overall_stability_score']
            accuracy_score = accuracy_analysis[seq_name]['overall_accuracy_score']
            realtime_score = realtime_analysis[seq_name]['feasibility_score']
            
            # Weighted overall score (temporal resolution weighted higher for neurofeedback)
            overall_score = (
                stability_score * 0.3 +
                accuracy_score * 0.3 +
                realtime_score * 0.4
            )
            
            summary[seq_name] = {
                'stability_score': stability_score,
                'accuracy_score': accuracy_score,
                'realtime_score': realtime_score,
                'overall_score': overall_score
            }
        
        return summary
    
    def visualize_sequence_comparison(self, steam_data: MRSData, semi_laser_data: MRSData,
                                    save_path: Optional[str] = None) -> None:
        """
        Create comprehensive visualization comparing sequences
        
        Args:
            steam_data: MRSData from STEAM sequence
            semi_laser_data: MRSData from semi-LASER sequence
            save_path: Optional path to save the figure
        """
        fig, axes = plt.subplots(3, 2, figsize=(15, 12))
        fig.suptitle('MRS Sequence Comparison: STEAM vs semi-LASER', fontsize=16, fontweight='bold')
        
        # Time series comparison
        ax1 = axes[0, 0]
        time_steam = steam_data.timestamps / 60  # Convert to minutes
        time_laser = semi_laser_data.timestamps / 60
        
        ax1.plot(time_steam, steam_data.ei_ratio, 'b-', label='STEAM', alpha=0.7)
        ax1.plot(time_laser, semi_laser_data.ei_ratio, 'r-', label='semi-LASER', alpha=0.7)
        ax1.set_xlabel('Time (minutes)')
        ax1.set_ylabel('E/I Ratio')
        ax1.set_title('E/I Ratio Time Series')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # Temporal resolution comparison
        ax2 = axes[0, 1]
        sequences = ['STEAM', 'semi-LASER']
        temporal_res = [steam_data.sequence_params.temporal_resolution,
                       semi_laser_data.sequence_params.temporal_resolution]
        colors = ['blue', 'red']
        
        bars = ax2.bar(sequences, temporal_res, color=colors, alpha=0.7)
        ax2.set_ylabel('Temporal Resolution (seconds)')
        ax2.set_title('Temporal Resolution Comparison')
        ax2.grid(True, alpha=0.3)
        
        # Add value labels on bars
        for bar, value in zip(bars, temporal_res):
            ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.1,
                    f'{value:.1f}s', ha='center', va='bottom')
        
        # Signal stability comparison
        ax3 = axes[1, 0]
        steam_cv = np.std(steam_data.ei_ratio) / np.mean(steam_data.ei_ratio)
        laser_cv = np.std(semi_laser_data.ei_ratio) / np.mean(semi_laser_data.ei_ratio)
        
        cv_values = [steam_cv, laser_cv]
        bars = ax3.bar(sequences, cv_values, color=colors, alpha=0.7)
        ax3.set_ylabel('Coefficient of Variation')
        ax3.set_title('Signal Stability (Lower is Better)')
        ax3.grid(True, alpha=0.3)
        
        for bar, value in zip(bars, cv_values):
            ax3.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.001,
                    f'{value:.3f}', ha='center', va='bottom')
        
        # SNR comparison
        ax4 = axes[1, 1]
        steam_snr = steam_data.sequence_params.theoretical_snr
        laser_snr = semi_laser_data.sequence_params.theoretical_snr
        
        snr_values = [steam_snr, laser_snr]
        bars = ax4.bar(sequences, snr_values, color=colors, alpha=0.7)
        ax4.set_ylabel('Theoretical SNR')
        ax4.set_title('Signal-to-Noise Ratio')
        ax4.grid(True, alpha=0.3)
        
        for bar, value in zip(bars, snr_values):
            ax4.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.01,
                    f'{value:.2f}', ha='center', va='bottom')
        
        # Metabolite concentrations comparison
        ax5 = axes[2, 0]
        metabolites = ['GABA', 'Glutamate', 'Glutamine']
        steam_concs = [np.mean(steam_data.gaba_concentration),
                      np.mean(steam_data.glutamate_concentration),
                      np.mean(steam_data.glutamine_concentration)]
        laser_concs = [np.mean(semi_laser_data.gaba_concentration),
                      np.mean(semi_laser_data.glutamate_concentration),
                      np.mean(semi_laser_data.glutamine_concentration)]
        
        x = np.arange(len(metabolites))
        width = 0.35
        
        ax5.bar(x - width/2, steam_concs, width, label='STEAM', color='blue', alpha=0.7)
        ax5.bar(x + width/2, laser_concs, width, label='semi-LASER', color='red', alpha=0.7)
        
        ax5.set_xlabel('Metabolite')
        ax5.set_ylabel('Concentration (IU)')
        ax5.set_title('Mean Metabolite Concentrations')
        ax5.set_xticks(x)
        ax5.set_xticklabels(metabolites)
        ax5.legend()
        ax5.grid(True, alpha=0.3)
        
        # Real-time feasibility radar chart
        ax6 = axes[2, 1]
        
        # Calculate metrics for radar chart
        steam_metrics = [
            steam_data.sequence_params.temporal_resolution,
            steam_snr,
            steam_cv,
            steam_data.sequence_params.sar_limit
        ]
        laser_metrics = [
            semi_laser_data.sequence_params.temporal_resolution,
            laser_snr,
            laser_cv,
            semi_laser_data.sequence_params.sar_limit
        ]
        
        # Normalize metrics (lower is better for temporal resolution, CV, SAR)
        # Higher is better for SNR
        steam_normalized = [
            10 / steam_metrics[0],  # Temporal resolution (inverted)
            steam_metrics[1] * 10,  # SNR
            1 / steam_metrics[2],   # CV (inverted)
            1 / steam_metrics[3]    # SAR (inverted)
        ]
        laser_normalized = [
            10 / laser_metrics[0],
            laser_metrics[1] * 10,
            1 / laser_metrics[2],
            1 / laser_metrics[3]
        ]
        
        categories = ['Temporal\nResolution', 'SNR', 'Stability', 'SAR\nLimitation']
        
        # Simple bar chart instead of radar for clarity
        x = np.arange(len(categories))
        ax6.bar(x - width/2, steam_normalized, width, label='STEAM', color='blue', alpha=0.7)
        ax6.bar(x + width/2, laser_normalized, width, label='semi-LASER', color='red', alpha=0.7)
        
        ax6.set_xlabel('Performance Metrics')
        ax6.set_ylabel('Normalized Score (Higher is Better)')
        ax6.set_title('Overall Performance Comparison')
        ax6.set_xticks(x)
        ax6.set_xticklabels(categories, rotation=45, ha='right')
        ax6.legend()
        ax6.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            logger.info(f"Visualization saved to {save_path}")
        
        plt.show()
    
    def save_analysis_results(self, results: Dict, output_path: str) -> None:
        """Save analysis results to JSON file"""
        
        # Convert numpy arrays to lists for JSON serialization
        def convert_numpy(obj):
            if isinstance(obj, np.ndarray):
                return obj.tolist()
            elif isinstance(obj, np.integer):
                return int(obj)
            elif isinstance(obj, np.floating):
                return float(obj)
            elif isinstance(obj, dict):
                return {key: convert_numpy(value) for key, value in obj.items()}
            elif isinstance(obj, list):
                return [convert_numpy(item) for item in obj]
            else:
                return obj
        
        serializable_results = convert_numpy(results)
        
        with open(output_path, 'w') as f:
            json.dump(serializable_results, f, indent=2)
        
        logger.info(f"Analysis results saved to {output_path}")

def main():
    """
    Main function demonstrating MRS sequence analysis
    """
    print("="*80)
    print("MRS SEQUENCE ANALYSIS FOR REAL-TIME NEUROFEEDBACK")
    print("Research: Managing Plasticity and Stability in Skill Learning")
    print("Author: Shusuke Okita, RIKEN CBS")
    print("="*80)
    
    # Initialize analyzer
    analyzer = MRSSequenceAnalyzer()
    
    # Define task periods for simulation (motor task at 2-4 min, visual task at 6-8 min)
    task_periods = [(2, 4), (6, 8)]
    
    # Simulate data for both sequences
    print("\n1. Simulating MRS data for sequence comparison...")
    steam_data = analyzer.simulate_mrs_measurement('STEAM', duration_minutes=10, task_periods=task_periods)
    semi_laser_data = analyzer.simulate_mrs_measurement('semi-LASER', duration_minutes=10, task_periods=task_periods)
    
    print(f"STEAM: {len(steam_data.timestamps)} measurements over {steam_data.duration_minutes:.1f} minutes")
    print(f"semi-LASER: {len(semi_laser_data.timestamps)} measurements over {semi_laser_data.duration_minutes:.1f} minutes")
    
    # Generate comprehensive comparison report
    print("\n2. Generating comprehensive comparison report...")
    report = analyzer.generate_comparison_report(steam_data, semi_laser_data)
    
    # Display key results
    print("\n3. KEY ANALYSIS RESULTS")
    print("-" * 40)
    
    print("\nTemporal Resolution:")
    for seq in ['STEAM', 'semi-LASER']:
        temp_res = report['temporal_resolution_analysis'][seq]['temporal_resolution_seconds']
        sampling_rate = report['temporal_resolution_analysis'][seq]['effective_sampling_rate']
        print(f"  {seq}: {temp_res:.1f}s ({sampling_rate:.2f} Hz)")
    
    print("\nSignal Stability Scores:")
    for seq in ['STEAM', 'semi-LASER']:
        stability = report['signal_stability_analysis'][seq]['overall_stability_score']
        print(f"  {seq}: {stability:.1f}/100")
    
    print("\nQuantification Accuracy Scores:")
    for seq in ['STEAM', 'semi-LASER']:
        accuracy = report['quantification_accuracy_analysis'][seq]['overall_accuracy_score']
        print(f"  {seq}: {accuracy:.1f}/100")
    
    print("\nReal-time Feasibility:")
    for seq in ['STEAM', 'semi-LASER']:
        feasibility = report['realtime_feasibility_analysis'][seq]['feasibility_score']
        latency = report['realtime_feasibility_analysis'][seq]['total_latency']
        print(f"  {seq}: {feasibility:.1f}/100 (latency: {latency:.1f}s)")
    
    print("\nOverall Summary Scores:")
    for seq in ['STEAM', 'semi-LASER']:
        overall = report['summary_scores'][seq]['overall_score']
        print(f"  {seq}: {overall:.1f}/100")
    
    print(f"\n4. RECOMMENDATION")
    print("-" * 40)
    print(f"Primary recommendation: {report['recommendations']['primary_recommendation']}")
    print(f"Rationale: {report['recommendations']['rationale']}")
    
    # Optimize parameters for recommended sequence
    recommended_seq = report['recommendations']['primary_recommendation']
    print(f"\n5. PARAMETER OPTIMIZATION FOR {recommended_seq}")
    print("-" * 40)
    
    optimization_result = analyzer.optimize_sequence_parameters(recommended_seq, 'balanced')
    optimized_params = optimization_result['optimized_sequence']
    
    print(f"Optimized parameters:")
    print(f"  TR: {optimized_params.tr:.1f}s")
    print(f"  Phase cycling: {optimized_params.phase_cycling}")
    print(f"  Temporal resolution: {optimized_params.temporal_resolution:.1f}s")
    print(f"  Theoretical SNR: {optimized_params.theoretical_snr:.2f}")
    print(f"  Optimization score: {optimization_result['optimization_score']:.1f}")
    
    # Create visualization
    print("\n6. Generating visualization...")
    analyzer.visualize_sequence_comparison(steam_data, semi_laser_data, 'mrs_sequence_comparison.png')
    
    # Save results
    print("\n7. Saving analysis results...")
    analyzer.save_analysis_results(report, 'mrs_sequence_analysis_report.json')
    
    print("\n" + "="*80)
    print("MRS SEQUENCE ANALYSIS COMPLETE")
    print("="*80)
    print("\nNext steps:")
    print("1. Validate findings with pilot MRS measurements")
    print("2. Test real-time processing pipeline with recommended sequence")
    print("3. Conduct region-specific (V1/M1) optimization")
    print("4. Implement quality control metrics for real-time monitoring")

if __name__ == "__main__":
    main() 