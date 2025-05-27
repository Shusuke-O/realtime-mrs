#!/usr/bin/env python3
"""
Data Analysis for Realtime MRS Experiments
Comprehensive analysis tools for processing recorded LSL experiment data.
"""

import os
import json
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
import warnings

# Suppress warnings for cleaner output
warnings.filterwarnings('ignore')

from logger import get_logger

logger = get_logger("DataAnalysis")

class ExperimentDataAnalyzer:
    """
    Comprehensive analyzer for experiment data recorded via LSL.
    
    This class provides:
    1. Data loading and preprocessing
    2. Synchronization across streams
    3. Statistical analysis
    4. Visualization
    5. Report generation
    """
    
    def __init__(self, data_directory: str):
        """
        Initialize the data analyzer.
        
        Args:
            data_directory: Path to the experiment data directory
        """
        self.data_directory = Path(data_directory)
        self.logger = logger
        
        # Data containers
        self.session_info: Optional[Dict[str, Any]] = None
        self.events_data: Optional[pd.DataFrame] = None
        self.mrs_data: Optional[pd.DataFrame] = None
        self.m1_data: Optional[pd.DataFrame] = None
        self.v1_data: Optional[pd.DataFrame] = None
        self.physio_data: Optional[pd.DataFrame] = None
        
        # Analysis results
        self.analysis_results: Dict[str, Any] = {}
        
        self.logger.info(f"Initialized data analyzer for: {data_directory}")
    
    def load_session_data(self) -> bool:
        """
        Load all session data from the directory.
        
        Returns:
            bool: True if data loaded successfully
        """
        try:
            # Load session info
            session_file = self.data_directory / 'session_info.json'
            if session_file.exists():
                with open(session_file, 'r') as f:
                    self.session_info = json.load(f)
                self.logger.info(f"Loaded session info: {self.session_info['participant_id']}/{self.session_info['session_id']}")
            
            # Load events
            events_file = self.data_directory / 'events.csv'
            if events_file.exists():
                self.events_data = pd.read_csv(events_file)
                self.events_data['timestamp'] = pd.to_datetime(self.events_data['timestamp'], unit='s')
                self.logger.info(f"Loaded {len(self.events_data)} events")
            
            # Load stream data
            self._load_stream_data()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error loading session data: {e}")
            return False
    
    def _load_stream_data(self):
        """Load data from individual LSL streams."""
        # Load FSL-MRS E/I ratio data
        mrs_files = list(self.data_directory.glob('FSL-MRS-EI-Ratio_*.csv'))
        if mrs_files:
            self.mrs_data = pd.read_csv(mrs_files[0])
            self.mrs_data['timestamp'] = pd.to_datetime(self.mrs_data['timestamp'], unit='s')
            self.mrs_data['ei_ratio'] = pd.to_numeric(self.mrs_data['data'], errors='coerce')
            self.logger.info(f"Loaded {len(self.mrs_data)} MRS data points")
        
        # Load M1 tapping task data
        m1_files = list(self.data_directory.glob('M1-Tapping-Task_*.csv'))
        if m1_files:
            self.m1_data = self._load_task_data(m1_files[0], 'm1_tapping')
            self.logger.info(f"Loaded {len(self.m1_data)} M1 task events")
        
        # Load V1 orientation task data
        v1_files = list(self.data_directory.glob('V1-Orientation-Task_*.csv'))
        if v1_files:
            self.v1_data = self._load_task_data(v1_files[0], 'v1_orientation')
            self.logger.info(f"Loaded {len(self.v1_data)} V1 task events")
        
        # Load physiological data
        physio_files = list(self.data_directory.glob('Physiological-Data_*.csv'))
        if physio_files:
            self.physio_data = self._load_physiological_data(physio_files[0])
            self.logger.info(f"Loaded {len(self.physio_data)} physiological data points")
    
    def _load_task_data(self, file_path: Path, task_type: str) -> pd.DataFrame:
        """Load and parse task data from CSV."""
        df = pd.read_csv(file_path)
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
        
        # Parse JSON data
        parsed_data = []
        for _, row in df.iterrows():
            try:
                event_data = json.loads(row['data'])
                event_data['timestamp'] = row['timestamp']
                parsed_data.append(event_data)
            except json.JSONDecodeError:
                continue
        
        return pd.DataFrame(parsed_data)
    
    def _load_physiological_data(self, file_path: Path) -> pd.DataFrame:
        """Load and parse physiological data from CSV."""
        df = pd.read_csv(file_path)
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
        
        # Parse comma-separated physiological values
        # Assuming format: heart_rate,eye_x,eye_y,pupil_diameter,blink
        physio_columns = ['heart_rate', 'eye_x', 'eye_y', 'pupil_diameter', 'blink']
        
        parsed_data = []
        for _, row in df.iterrows():
            try:
                values = [float(x) for x in row['data'].split(',')]
                data_dict = {'timestamp': row['timestamp']}
                for i, col in enumerate(physio_columns):
                    if i < len(values):
                        data_dict[col] = values[i]
                parsed_data.append(data_dict)
            except (ValueError, AttributeError):
                continue
        
        return pd.DataFrame(parsed_data)
    
    def analyze_mrs_data(self) -> Dict[str, Any]:
        """Analyze FSL-MRS E/I ratio data."""
        if self.mrs_data is None or self.mrs_data.empty:
            self.logger.warning("No MRS data available for analysis")
            return {}
        
        results = {}
        
        # Basic statistics
        ei_ratios = self.mrs_data['ei_ratio'].dropna()
        results['basic_stats'] = {
            'mean_ei_ratio': float(ei_ratios.mean()),
            'std_ei_ratio': float(ei_ratios.std()),
            'min_ei_ratio': float(ei_ratios.min()),
            'max_ei_ratio': float(ei_ratios.max()),
            'median_ei_ratio': float(ei_ratios.median()),
            'n_samples': len(ei_ratios)
        }
        
        # Temporal analysis
        if len(ei_ratios) > 1:
            # Calculate rate of change
            time_diff = self.mrs_data['timestamp'].diff().dt.total_seconds()
            ei_diff = self.mrs_data['ei_ratio'].diff()
            rate_of_change = ei_diff / time_diff
            
            results['temporal_analysis'] = {
                'mean_rate_of_change': float(rate_of_change.mean()),
                'std_rate_of_change': float(rate_of_change.std()),
                'max_rate_of_change': float(rate_of_change.max()),
                'min_rate_of_change': float(rate_of_change.min())
            }
            
            # Trend analysis
            time_numeric = (self.mrs_data['timestamp'] - self.mrs_data['timestamp'].iloc[0]).dt.total_seconds()
            correlation = np.corrcoef(time_numeric, ei_ratios)[0, 1]
            results['trend_analysis'] = {
                'time_correlation': float(correlation),
                'trend_direction': 'increasing' if correlation > 0.1 else 'decreasing' if correlation < -0.1 else 'stable'
            }
        
        self.analysis_results['mrs_analysis'] = results
        self.logger.info("Completed MRS data analysis")
        return results
    
    def analyze_task_performance(self) -> Dict[str, Any]:
        """Analyze task performance data."""
        results = {}
        
        # Analyze M1 tapping task
        if self.m1_data is not None and not self.m1_data.empty:
            results['m1_tapping'] = self._analyze_m1_performance()
        
        # Analyze V1 orientation task
        if self.v1_data is not None and not self.v1_data.empty:
            results['v1_orientation'] = self._analyze_v1_performance()
        
        self.analysis_results['task_performance'] = results
        self.logger.info("Completed task performance analysis")
        return results
    
    def _analyze_m1_performance(self) -> Dict[str, Any]:
        """Analyze M1 tapping task performance."""
        # Filter tap events
        tap_events = self.m1_data[self.m1_data['event_type'] == 'tap'].copy()
        
        if tap_events.empty:
            return {'error': 'No tap events found'}
        
        # Calculate accuracy
        accuracy = tap_events['is_correct'].mean() if 'is_correct' in tap_events.columns else None
        
        # Calculate reaction times
        reaction_times = tap_events['reaction_time'].dropna()
        
        results = {
            'total_taps': len(tap_events),
            'accuracy': float(accuracy) if accuracy is not None else None,
            'mean_reaction_time': float(reaction_times.mean()) if not reaction_times.empty else None,
            'std_reaction_time': float(reaction_times.std()) if not reaction_times.empty else None,
            'median_reaction_time': float(reaction_times.median()) if not reaction_times.empty else None
        }
        
        # Trial-by-trial analysis
        if 'trial_number' in tap_events.columns:
            trial_stats = tap_events.groupby('trial_number').agg({
                'is_correct': 'mean',
                'reaction_time': ['mean', 'std']
            }).round(3)
            results['trial_performance'] = trial_stats.to_dict()
        
        return results
    
    def _analyze_v1_performance(self) -> Dict[str, Any]:
        """Analyze V1 orientation task performance."""
        # Filter response events
        response_events = self.v1_data[self.v1_data['event_type'] == 'response'].copy()
        
        if response_events.empty:
            return {'error': 'No response events found'}
        
        # Calculate accuracy
        accuracy = response_events['is_correct'].mean() if 'is_correct' in response_events.columns else None
        
        # Calculate reaction times
        reaction_times = response_events['reaction_time'].dropna()
        
        results = {
            'total_responses': len(response_events),
            'accuracy': float(accuracy) if accuracy is not None else None,
            'mean_reaction_time': float(reaction_times.mean()) if not reaction_times.empty else None,
            'std_reaction_time': float(reaction_times.std()) if not reaction_times.empty else None,
            'median_reaction_time': float(reaction_times.median()) if not reaction_times.empty else None
        }
        
        # Trial-by-trial analysis
        if 'trial_number' in response_events.columns:
            trial_stats = response_events.groupby('trial_number').agg({
                'is_correct': 'mean',
                'reaction_time': ['mean', 'std']
            }).round(3)
            results['trial_performance'] = trial_stats.to_dict()
        
        return results
    
    def analyze_mrs_task_correlation(self) -> Dict[str, Any]:
        """Analyze correlation between MRS data and task performance."""
        if self.mrs_data is None or self.mrs_data.empty:
            return {'error': 'No MRS data available'}
        
        results = {}
        
        # Correlate with M1 task
        if self.m1_data is not None and not self.m1_data.empty:
            results['m1_correlation'] = self._correlate_mrs_with_task(self.m1_data, 'm1')
        
        # Correlate with V1 task
        if self.v1_data is not None and not self.v1_data.empty:
            results['v1_correlation'] = self._correlate_mrs_with_task(self.v1_data, 'v1')
        
        self.analysis_results['mrs_task_correlation'] = results
        self.logger.info("Completed MRS-task correlation analysis")
        return results
    
    def _correlate_mrs_with_task(self, task_data: pd.DataFrame, task_name: str) -> Dict[str, Any]:
        """Correlate MRS data with task performance."""
        try:
            # Get task events with performance metrics
            if task_name == 'm1':
                perf_events = task_data[task_data['event_type'] == 'tap'].copy()
            else:  # v1
                perf_events = task_data[task_data['event_type'] == 'response'].copy()
            
            if perf_events.empty:
                return {'error': f'No performance events found for {task_name}'}
            
            # For each task event, find the closest MRS measurement
            correlations = []
            
            for _, event in perf_events.iterrows():
                event_time = event['timestamp']
                
                # Find closest MRS measurement (within 30 seconds)
                time_diff = abs(self.mrs_data['timestamp'] - event_time)
                closest_idx = time_diff.idxmin()
                
                if time_diff.iloc[closest_idx].total_seconds() <= 30:  # Within 30 seconds
                    mrs_value = self.mrs_data.loc[closest_idx, 'ei_ratio']
                    
                    correlation_data = {
                        'timestamp': event_time,
                        'ei_ratio': mrs_value,
                        'reaction_time': event.get('reaction_time'),
                        'is_correct': event.get('is_correct'),
                        'time_diff_seconds': time_diff.iloc[closest_idx].total_seconds()
                    }
                    correlations.append(correlation_data)
            
            if not correlations:
                return {'error': 'No temporal matches found between MRS and task data'}
            
            corr_df = pd.DataFrame(correlations)
            
            # Calculate correlations
            results = {}
            
            if 'reaction_time' in corr_df.columns:
                rt_corr = corr_df[['ei_ratio', 'reaction_time']].corr().iloc[0, 1]
                results['ei_reaction_time_correlation'] = float(rt_corr) if not np.isnan(rt_corr) else None
            
            if 'is_correct' in corr_df.columns:
                acc_corr = corr_df[['ei_ratio', 'is_correct']].corr().iloc[0, 1]
                results['ei_accuracy_correlation'] = float(acc_corr) if not np.isnan(acc_corr) else None
            
            results['n_matched_events'] = len(corr_df)
            results['mean_time_diff'] = float(corr_df['time_diff_seconds'].mean())
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error in MRS-task correlation for {task_name}: {e}")
            return {'error': str(e)}
    
    def generate_visualizations(self, output_dir: Optional[str] = None) -> bool:
        """Generate comprehensive visualizations."""
        if output_dir is None:
            output_dir = self.data_directory / 'analysis_plots'
        else:
            output_dir = Path(output_dir)
        
        output_dir.mkdir(exist_ok=True)
        
        try:
            # Set style
            plt.style.use('seaborn-v0_8')
            sns.set_palette("husl")
            
            # MRS data visualization
            if self.mrs_data is not None and not self.mrs_data.empty:
                self._plot_mrs_timeseries(output_dir)
                self._plot_mrs_distribution(output_dir)
            
            # Task performance visualization
            if self.m1_data is not None and not self.m1_data.empty:
                self._plot_m1_performance(output_dir)
            
            if self.v1_data is not None and not self.v1_data.empty:
                self._plot_v1_performance(output_dir)
            
            # Correlation plots
            self._plot_correlations(output_dir)
            
            # Summary dashboard
            self._create_summary_dashboard(output_dir)
            
            self.logger.info(f"Generated visualizations in: {output_dir}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error generating visualizations: {e}")
            return False
    
    def _plot_mrs_timeseries(self, output_dir: Path):
        """Plot MRS E/I ratio time series."""
        fig, ax = plt.subplots(figsize=(12, 6))
        
        ax.plot(self.mrs_data['timestamp'], self.mrs_data['ei_ratio'], 
                linewidth=2, alpha=0.8, label='E/I Ratio')
        
        # Add trend line
        time_numeric = (self.mrs_data['timestamp'] - self.mrs_data['timestamp'].iloc[0]).dt.total_seconds()
        z = np.polyfit(time_numeric, self.mrs_data['ei_ratio'].dropna(), 1)
        p = np.poly1d(z)
        ax.plot(self.mrs_data['timestamp'], p(time_numeric), 
                "--", alpha=0.8, color='red', label='Trend')
        
        ax.set_xlabel('Time')
        ax.set_ylabel('E/I Ratio')
        ax.set_title('FSL-MRS E/I Ratio Over Time')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(output_dir / 'mrs_timeseries.png', dpi=300, bbox_inches='tight')
        plt.close()
    
    def _plot_mrs_distribution(self, output_dir: Path):
        """Plot MRS E/I ratio distribution."""
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
        
        # Histogram
        ax1.hist(self.mrs_data['ei_ratio'].dropna(), bins=20, alpha=0.7, edgecolor='black')
        ax1.set_xlabel('E/I Ratio')
        ax1.set_ylabel('Frequency')
        ax1.set_title('E/I Ratio Distribution')
        ax1.grid(True, alpha=0.3)
        
        # Box plot
        ax2.boxplot(self.mrs_data['ei_ratio'].dropna())
        ax2.set_ylabel('E/I Ratio')
        ax2.set_title('E/I Ratio Box Plot')
        ax2.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(output_dir / 'mrs_distribution.png', dpi=300, bbox_inches='tight')
        plt.close()
    
    def _plot_m1_performance(self, output_dir: Path):
        """Plot M1 tapping task performance."""
        tap_events = self.m1_data[self.m1_data['event_type'] == 'tap'].copy()
        
        if tap_events.empty:
            return
        
        fig, axes = plt.subplots(2, 2, figsize=(12, 10))
        
        # Reaction time over trials
        if 'trial_number' in tap_events.columns and 'reaction_time' in tap_events.columns:
            trial_rt = tap_events.groupby('trial_number')['reaction_time'].mean()
            axes[0, 0].plot(trial_rt.index, trial_rt.values, 'o-')
            axes[0, 0].set_xlabel('Trial Number')
            axes[0, 0].set_ylabel('Mean Reaction Time (s)')
            axes[0, 0].set_title('M1 Reaction Time by Trial')
            axes[0, 0].grid(True, alpha=0.3)
        
        # Accuracy over trials
        if 'trial_number' in tap_events.columns and 'is_correct' in tap_events.columns:
            trial_acc = tap_events.groupby('trial_number')['is_correct'].mean()
            axes[0, 1].plot(trial_acc.index, trial_acc.values, 'o-', color='green')
            axes[0, 1].set_xlabel('Trial Number')
            axes[0, 1].set_ylabel('Accuracy')
            axes[0, 1].set_title('M1 Accuracy by Trial')
            axes[0, 1].set_ylim(0, 1)
            axes[0, 1].grid(True, alpha=0.3)
        
        # Reaction time distribution
        if 'reaction_time' in tap_events.columns:
            axes[1, 0].hist(tap_events['reaction_time'].dropna(), bins=15, alpha=0.7, edgecolor='black')
            axes[1, 0].set_xlabel('Reaction Time (s)')
            axes[1, 0].set_ylabel('Frequency')
            axes[1, 0].set_title('M1 Reaction Time Distribution')
            axes[1, 0].grid(True, alpha=0.3)
        
        # Accuracy by sequence position
        if 'sequence_position' in tap_events.columns and 'is_correct' in tap_events.columns:
            pos_acc = tap_events.groupby('sequence_position')['is_correct'].mean()
            axes[1, 1].bar(pos_acc.index, pos_acc.values, alpha=0.7)
            axes[1, 1].set_xlabel('Sequence Position')
            axes[1, 1].set_ylabel('Accuracy')
            axes[1, 1].set_title('M1 Accuracy by Sequence Position')
            axes[1, 1].grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(output_dir / 'm1_performance.png', dpi=300, bbox_inches='tight')
        plt.close()
    
    def _plot_v1_performance(self, output_dir: Path):
        """Plot V1 orientation task performance."""
        response_events = self.v1_data[self.v1_data['event_type'] == 'response'].copy()
        
        if response_events.empty:
            return
        
        fig, axes = plt.subplots(2, 2, figsize=(12, 10))
        
        # Reaction time over trials
        if 'trial_number' in response_events.columns and 'reaction_time' in response_events.columns:
            trial_rt = response_events.groupby('trial_number')['reaction_time'].mean()
            axes[0, 0].plot(trial_rt.index, trial_rt.values, 'o-')
            axes[0, 0].set_xlabel('Trial Number')
            axes[0, 0].set_ylabel('Mean Reaction Time (s)')
            axes[0, 0].set_title('V1 Reaction Time by Trial')
            axes[0, 0].grid(True, alpha=0.3)
        
        # Accuracy over trials
        if 'trial_number' in response_events.columns and 'is_correct' in response_events.columns:
            trial_acc = response_events.groupby('trial_number')['is_correct'].mean()
            axes[0, 1].plot(trial_acc.index, trial_acc.values, 'o-', color='green')
            axes[0, 1].set_xlabel('Trial Number')
            axes[0, 1].set_ylabel('Accuracy')
            axes[0, 1].set_title('V1 Accuracy by Trial')
            axes[0, 1].set_ylim(0, 1)
            axes[0, 1].grid(True, alpha=0.3)
        
        # Reaction time distribution
        if 'reaction_time' in response_events.columns:
            axes[1, 0].hist(response_events['reaction_time'].dropna(), bins=15, alpha=0.7, edgecolor='black')
            axes[1, 0].set_xlabel('Reaction Time (s)')
            axes[1, 0].set_ylabel('Frequency')
            axes[1, 0].set_title('V1 Reaction Time Distribution')
            axes[1, 0].grid(True, alpha=0.3)
        
        # Overall accuracy
        if 'is_correct' in response_events.columns:
            accuracy = response_events['is_correct'].mean()
            axes[1, 1].bar(['Correct', 'Incorrect'], [accuracy, 1-accuracy], alpha=0.7)
            axes[1, 1].set_ylabel('Proportion')
            axes[1, 1].set_title('V1 Overall Accuracy')
            axes[1, 1].grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(output_dir / 'v1_performance.png', dpi=300, bbox_inches='tight')
        plt.close()
    
    def _plot_correlations(self, output_dir: Path):
        """Plot MRS-task correlations."""
        if 'mrs_task_correlation' not in self.analysis_results:
            return
        
        corr_results = self.analysis_results['mrs_task_correlation']
        
        fig, axes = plt.subplots(1, 2, figsize=(12, 5))
        
        # M1 correlations
        if 'm1_correlation' in corr_results:
            m1_corr = corr_results['m1_correlation']
            if 'ei_reaction_time_correlation' in m1_corr and m1_corr['ei_reaction_time_correlation'] is not None:
                axes[0].bar(['E/I vs RT'], [m1_corr['ei_reaction_time_correlation']], alpha=0.7)
                axes[0].set_ylabel('Correlation Coefficient')
                axes[0].set_title('M1 Task: E/I Ratio vs Performance')
                axes[0].set_ylim(-1, 1)
                axes[0].grid(True, alpha=0.3)
        
        # V1 correlations
        if 'v1_correlation' in corr_results:
            v1_corr = corr_results['v1_correlation']
            if 'ei_reaction_time_correlation' in v1_corr and v1_corr['ei_reaction_time_correlation'] is not None:
                axes[1].bar(['E/I vs RT'], [v1_corr['ei_reaction_time_correlation']], alpha=0.7)
                axes[1].set_ylabel('Correlation Coefficient')
                axes[1].set_title('V1 Task: E/I Ratio vs Performance')
                axes[1].set_ylim(-1, 1)
                axes[1].grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(output_dir / 'correlations.png', dpi=300, bbox_inches='tight')
        plt.close()
    
    def _create_summary_dashboard(self, output_dir: Path):
        """Create a summary dashboard with key metrics."""
        fig = plt.figure(figsize=(16, 12))
        
        # Create a grid layout
        gs = fig.add_gridspec(3, 3, hspace=0.3, wspace=0.3)
        
        # MRS summary
        if self.mrs_data is not None and not self.mrs_data.empty:
            ax1 = fig.add_subplot(gs[0, :])
            ax1.plot(self.mrs_data['timestamp'], self.mrs_data['ei_ratio'], linewidth=2)
            ax1.set_title('E/I Ratio Timeline', fontsize=14, fontweight='bold')
            ax1.set_ylabel('E/I Ratio')
            ax1.grid(True, alpha=0.3)
        
        # Task performance summaries
        if 'task_performance' in self.analysis_results:
            task_perf = self.analysis_results['task_performance']
            
            # M1 performance
            if 'm1_tapping' in task_perf:
                ax2 = fig.add_subplot(gs[1, 0])
                m1_data = task_perf['m1_tapping']
                metrics = ['Accuracy', 'Mean RT']
                values = [m1_data.get('accuracy', 0), m1_data.get('mean_reaction_time', 0)]
                ax2.bar(metrics, values, alpha=0.7)
                ax2.set_title('M1 Tapping Performance', fontweight='bold')
                ax2.grid(True, alpha=0.3)
            
            # V1 performance
            if 'v1_orientation' in task_perf:
                ax3 = fig.add_subplot(gs[1, 1])
                v1_data = task_perf['v1_orientation']
                metrics = ['Accuracy', 'Mean RT']
                values = [v1_data.get('accuracy', 0), v1_data.get('mean_reaction_time', 0)]
                ax3.bar(metrics, values, alpha=0.7)
                ax3.set_title('V1 Orientation Performance', fontweight='bold')
                ax3.grid(True, alpha=0.3)
        
        # MRS statistics
        if 'mrs_analysis' in self.analysis_results:
            ax4 = fig.add_subplot(gs[1, 2])
            mrs_stats = self.analysis_results['mrs_analysis']['basic_stats']
            stats = ['Mean', 'Std', 'Min', 'Max']
            values = [mrs_stats['mean_ei_ratio'], mrs_stats['std_ei_ratio'], 
                     mrs_stats['min_ei_ratio'], mrs_stats['max_ei_ratio']]
            ax4.bar(stats, values, alpha=0.7)
            ax4.set_title('E/I Ratio Statistics', fontweight='bold')
            ax4.grid(True, alpha=0.3)
        
        # Session info
        ax5 = fig.add_subplot(gs[2, :])
        ax5.axis('off')
        
        if self.session_info:
            info_text = f"""
            Session Information:
            Participant: {self.session_info.get('participant_id', 'N/A')}
            Session: {self.session_info.get('session_id', 'N/A')}
            Start Time: {self.session_info.get('start_time', 'N/A')}
            Duration: {self.session_info.get('duration_seconds', 'N/A')} seconds
            """
            ax5.text(0.1, 0.5, info_text, fontsize=12, verticalalignment='center',
                    bbox=dict(boxstyle="round,pad=0.3", facecolor="lightgray", alpha=0.5))
        
        plt.suptitle('Experiment Summary Dashboard', fontsize=16, fontweight='bold')
        plt.savefig(output_dir / 'summary_dashboard.png', dpi=300, bbox_inches='tight')
        plt.close()
    
    def generate_report(self, output_file: Optional[str] = None) -> bool:
        """Generate a comprehensive analysis report."""
        if output_file is None:
            output_file = self.data_directory / 'analysis_report.json'
        else:
            output_file = Path(output_file)
        
        try:
            # Compile all analysis results
            report = {
                'session_info': self.session_info,
                'analysis_timestamp': datetime.now().isoformat(),
                'data_summary': {
                    'mrs_data_points': len(self.mrs_data) if self.mrs_data is not None else 0,
                    'm1_events': len(self.m1_data) if self.m1_data is not None else 0,
                    'v1_events': len(self.v1_data) if self.v1_data is not None else 0,
                    'physio_data_points': len(self.physio_data) if self.physio_data is not None else 0,
                    'total_events': len(self.events_data) if self.events_data is not None else 0
                },
                'analysis_results': self.analysis_results
            }
            
            # Save report
            with open(output_file, 'w') as f:
                json.dump(report, f, indent=2, default=str)
            
            self.logger.info(f"Generated analysis report: {output_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error generating report: {e}")
            return False
    
    def run_complete_analysis(self, generate_plots: bool = True, 
                            generate_report: bool = True) -> bool:
        """Run complete analysis pipeline."""
        try:
            self.logger.info("Starting complete analysis pipeline...")
            
            # Load data
            if not self.load_session_data():
                self.logger.error("Failed to load session data")
                return False
            
            # Run analyses
            self.analyze_mrs_data()
            self.analyze_task_performance()
            self.analyze_mrs_task_correlation()
            
            # Generate outputs
            if generate_plots:
                self.generate_visualizations()
            
            if generate_report:
                self.generate_report()
            
            self.logger.info("Complete analysis pipeline finished successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Error in complete analysis pipeline: {e}")
            return False

def main():
    """Test the data analysis system."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Analyze experiment data')
    parser.add_argument('data_directory', help='Path to experiment data directory')
    parser.add_argument('--no-plots', action='store_true', help='Skip plot generation')
    parser.add_argument('--no-report', action='store_true', help='Skip report generation')
    
    args = parser.parse_args()
    
    # Create analyzer
    analyzer = ExperimentDataAnalyzer(args.data_directory)
    
    # Run analysis
    success = analyzer.run_complete_analysis(
        generate_plots=not args.no_plots,
        generate_report=not args.no_report
    )
    
    if success:
        print("Analysis completed successfully!")
    else:
        print("Analysis failed. Check logs for details.")

if __name__ == "__main__":
    main() 