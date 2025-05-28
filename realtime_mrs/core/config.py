"""
Configuration management for the realtime-mrs package.

Provides centralized configuration loading and management with support for:
- YAML configuration files
- Environment variable overrides
- Default configuration values
- Configuration validation
"""

import yaml
import os
from pathlib import Path
from typing import Any, Dict, Optional, Union, List
import copy

from .logger import get_logger

logger = get_logger(__name__)

class ConfigManager:
    """
    Configuration manager for the realtime-mrs package.
    
    Supports loading configuration from multiple sources with precedence:
    1. Explicitly provided config dict
    2. Environment variables (with REALTIME_MRS_ prefix)
    3. User config file (~/.realtime_mrs/config.yaml)
    4. Project config file (config.yaml in project root)
    5. Package default config
    """
    
    def __init__(self, config_file: Optional[Union[str, Path]] = None):
        """
        Initialize the configuration manager.
        
        Args:
            config_file: Optional path to configuration file
        """
        self._config_cache = None
        self._config_file = Path(config_file) if config_file else None
        self._default_config = self._get_default_config()
        
    def _get_default_config(self) -> Dict[str, Any]:
        """Get the default configuration."""
        return {
            'global': {
                'participant_id': 'default_participant',
                'session_id': 'session_001',
                'data_dir': 'data',
                'log_level': 'INFO',
            },
            'network': {
                'ip': '127.0.0.1',
                'port': 12345,
                'timeout': 5.0,
            },
            'display': {
                'window_size': [800, 600],
                'fullscreen': False,
                'background_color': 'black',
                'text_color': 'white',
                'text_height': 24,
            },
            'lsl': {
                'stream_name': 'RealtimeMRS',
                'stream_type': 'EI_Ratio',
                'source_id': 'realtime-mrs-001',
                'sampling_rate': 1.0,
                'buffer_size': 100,
            },
            'fsl_mrs_lsl': {
                'stream_name': 'FSL-MRS-EI-Ratio',
                'stream_type': 'EI_Ratio',
                'source_id': 'fsl-mrs-ei-001',
                'sampling_rate': 1.0,
                'simulation_mode': True,
                'simulation_range': [0.3, 1.2],
                'simulation_noise': 0.05,
            },
            'fsl_mrs': {
                'data_path': None,
                'basis_set_path': None,
                'fitting_params': {},
                'noise_level': 0.03,
                'temporal_variation': 0.1,
                'drift_enabled': True,
                'physiological_constraints': True,
                'spectrum_simulation': True,
            },
            'm1_task': {
                'controller': 'keyboard',
                'joystick_device': '',
                'repetitions': 3,
                'sequence': ['4', '1', '3', '2', '4'],
                'sequence_display_time': 2,
                'response_cutoff_time': 5,
                'randomize_sequence': False,
            },
            'v1_task': {
                'stimulus_duration': 0.1,
                'n_trials': 20,
                'response_cutoff_time': 3,
                'orientations': [0, 45, 90, 135],
                'stimulus_size': 100,
            },
            'ei_display': {
                'circle_base_size': 100,
                'circle_max_size': 300,
                'circle_color': 'white',
                'update_rate': 30,
                'smoothing_factor': 0.1,
            },
            'data_recording': {
                'auto_save': True,
                'save_format': 'csv',
                'backup_enabled': True,
                'compression': False,
            },
        }
    
    def _find_config_files(self) -> List[Path]:
        """Find all possible configuration files in order of precedence."""
        config_files = []
        
        # 1. Explicitly provided config file
        if self._config_file and self._config_file.exists():
            config_files.append(self._config_file)
        
        # 2. User config file
        user_config = Path.home() / '.realtime_mrs' / 'config.yaml'
        if user_config.exists():
            config_files.append(user_config)
        
        # 3. Project config file (in current working directory)
        project_config = Path.cwd() / 'config.yaml'
        if project_config.exists():
            config_files.append(project_config)
        
        # 4. Package config file (in package directory)
        package_root = Path(__file__).parent.parent.parent
        package_config = package_root / 'config.yaml'
        if package_config.exists():
            config_files.append(package_config)
        
        return config_files
    
    def _load_config_file(self, config_file: Path) -> Dict[str, Any]:
        """Load configuration from a YAML file."""
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f) or {}
            logger.debug(f"Loaded config from {config_file}")
            return config
        except Exception as e:
            logger.warning(f"Failed to load config from {config_file}: {e}")
            return {}
    
    def _merge_configs(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively merge two configuration dictionaries."""
        result = copy.deepcopy(base)
        
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_configs(result[key], value)
            else:
                result[key] = copy.deepcopy(value)
        
        return result
    
    def _load_env_overrides(self) -> Dict[str, Any]:
        """Load configuration overrides from environment variables."""
        env_config = {}
        prefix = 'REALTIME_MRS_'
        
        for key, value in os.environ.items():
            if key.startswith(prefix):
                # Convert REALTIME_MRS_NETWORK_IP to ['network', 'ip']
                config_path = key[len(prefix):].lower().split('_')
                
                # Try to convert value to appropriate type
                try:
                    # Try int first
                    if value.isdigit():
                        value = int(value)
                    # Try float
                    elif '.' in value and value.replace('.', '').isdigit():
                        value = float(value)
                    # Try boolean
                    elif value.lower() in ('true', 'false'):
                        value = value.lower() == 'true'
                    # Keep as string otherwise
                except ValueError:
                    pass
                
                # Set the value in the config dict
                current = env_config
                for part in config_path[:-1]:
                    if part not in current:
                        current[part] = {}
                    current = current[part]
                current[config_path[-1]] = value
        
        return env_config
    
    def load_config(self, force_reload: bool = False) -> Dict[str, Any]:
        """
        Load the complete configuration from all sources.
        
        Args:
            force_reload: Force reloading even if cached
            
        Returns:
            Complete configuration dictionary
        """
        if self._config_cache is not None and not force_reload:
            return self._config_cache
        
        # Start with default config
        config = copy.deepcopy(self._default_config)
        
        # Load and merge config files (in reverse order of precedence)
        config_files = self._find_config_files()
        for config_file in reversed(config_files):
            file_config = self._load_config_file(config_file)
            config = self._merge_configs(config, file_config)
        
        # Apply environment variable overrides
        env_config = self._load_env_overrides()
        if env_config:
            config = self._merge_configs(config, env_config)
            logger.debug("Applied environment variable overrides")
        
        self._config_cache = config
        logger.info(f"Configuration loaded from {len(config_files)} files")
        
        return config
    
    def get_config(self, path: str, default: Any = None) -> Any:
        """
        Get a configuration value by dot-separated path.
        
        Args:
            path: Dot-separated path (e.g., 'network.ip')
            default: Default value if not found
            
        Returns:
            Configuration value or default
        """
        config = self.load_config()
        keys = path.split('.')
        value = config
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        
        return value
    
    def set_config(self, path: str, value: Any):
        """
        Set a configuration value by dot-separated path.
        
        Args:
            path: Dot-separated path (e.g., 'network.ip')
            value: Value to set
        """
        config = self.load_config()
        keys = path.split('.')
        current = config
        
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        
        current[keys[-1]] = value
        self._config_cache = config
    
    def save_config(self, config_file: Optional[Union[str, Path]] = None):
        """
        Save the current configuration to a file.
        
        Args:
            config_file: Path to save config to. If None, uses user config location.
        """
        if config_file is None:
            config_file = Path.home() / '.realtime_mrs' / 'config.yaml'
        else:
            config_file = Path(config_file)
        
        # Ensure directory exists
        config_file.parent.mkdir(parents=True, exist_ok=True)
        
        config = self.load_config()
        
        try:
            with open(config_file, 'w', encoding='utf-8') as f:
                yaml.dump(config, f, default_flow_style=False, indent=2)
            logger.info(f"Configuration saved to {config_file}")
        except Exception as e:
            logger.error(f"Failed to save config to {config_file}: {e}")
            raise

# Global configuration manager instance
_config_manager = ConfigManager()

# Convenience functions for backward compatibility
def load_config(config_file: Optional[Union[str, Path]] = None) -> Dict[str, Any]:
    """Load configuration from file or use default."""
    global _config_manager
    if config_file:
        _config_manager = ConfigManager(config_file)
    return _config_manager.load_config()

def get_config(path: str, default: Any = None) -> Any:
    """Get a configuration value by dot-separated path."""
    return _config_manager.get_config(path, default)

def set_config(path: str, value: Any):
    """Set a configuration value by dot-separated path."""
    _config_manager.set_config(path, value)

def save_config(config_file: Optional[Union[str, Path]] = None):
    """Save the current configuration to a file."""
    _config_manager.save_config(config_file) 