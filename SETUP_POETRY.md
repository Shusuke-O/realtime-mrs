# Quick Setup Guide for Poetry Users

This guide helps you get started with the realtime-mrs system using Poetry for dependency management.

## Prerequisites

1. **Python 3.8+**
2. **Poetry** - Install if you haven't already:
   ```bash
   curl -sSL https://install.python-poetry.org | python3 -
   ```

## Quick Start

1. **Clone and setup the project:**
   ```bash
   cd realtime-mrs
   poetry install
   ```

2. **Test the LSL system:**
   ```bash
   poetry run test-lsl
   ```

3. **Run the main application:**
   ```bash
   poetry run realtime-mrs
   # Or alternatively:
   poetry run python menu.py
   ```

## Available Poetry Commands

### Main Application
```bash
poetry run realtime-mrs          # Start the main menu system
```

### Testing
```bash
poetry run test-lsl              # Test the complete LSL pipeline
```

### Individual Components
```bash
poetry run fsl-mrs-publisher --simulation    # Run FSL-MRS publisher in simulation mode
poetry run lsl-receiver                      # Run LSL receiver
```

### Development
```bash
poetry run python -m pytest     # Run tests (if available)
poetry run black .              # Format code
poetry run flake8 .             # Lint code
poetry run mypy .               # Type checking
```

## Configuration

The system uses `config.yaml` for configuration. Key settings for LSL integration:

```yaml
# Enable simulation mode for testing without real FSL-MRS
fsl_mrs_lsl:
  simulation_mode: true
  sampling_rate: 1.0

# LSL receiver settings
lsl_ei_receiver:
  forward_enabled: true
  forward_host: '127.0.0.1'
  forward_port: 5005
```

## Troubleshooting

### Common Issues

1. **Poetry not found:**
   ```bash
   # Add Poetry to your PATH or use full path
   ~/.local/bin/poetry install
   ```

2. **FSL-MRS import errors:**
   ```bash
   # Install with FSL-MRS support
   poetry install --extras fsl-mrs
   ```

3. **LSL library issues:**
   ```bash
   # On macOS, install LSL library
   brew install labstreaminglayer/tap/lsl
   ```

### Virtual Environment

Poetry automatically manages virtual environments. To activate manually:

```bash
poetry shell                     # Activate the virtual environment
python menu.py                  # Run directly in the activated environment
exit                            # Deactivate the environment
```

### Dependency Management

```bash
poetry add package-name          # Add a new dependency
poetry remove package-name       # Remove a dependency
poetry update                    # Update all dependencies
poetry show                      # List installed packages
poetry show --tree              # Show dependency tree
```

## Next Steps

1. **Test the system:** Run `poetry run test-lsl` to verify everything works
2. **Configure for your setup:** Edit `config.yaml` as needed
3. **Run the application:** Use `poetry run realtime-mrs` to start
4. **For real FSL-MRS:** Set `simulation_mode: false` in config and provide data paths

For detailed information about the LSL integration, see `README_LSL_Integration.md`. 