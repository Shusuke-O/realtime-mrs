import yaml
import os

_CONFIG_CACHE = None

CONFIG_PATH = os.path.join(os.path.dirname(__file__), 'config.yaml')

def load_config():
    global _CONFIG_CACHE
    if _CONFIG_CACHE is not None:
        return _CONFIG_CACHE
    with open(CONFIG_PATH, 'r') as f:
        _CONFIG_CACHE = yaml.safe_load(f)
    return _CONFIG_CACHE

def get_config(path, default=None):
    """
    Get a config value by dot-separated path, e.g. 'network.ip'.
    Returns default if not found.
    """
    config = load_config()
    keys = path.split('.')
    val = config
    for key in keys:
        if isinstance(val, dict) and key in val:
            val = val[key]
        else:
            return default
    return val 