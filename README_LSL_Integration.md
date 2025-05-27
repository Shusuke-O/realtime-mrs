# FSL-MRS Lab Streaming Layer (LSL) Integration

This document describes the integration of FSL-MRS with the realtime MRS visualization system using Lab Streaming Layer (LSL) for real-time data streaming.

## Overview

The LSL integration provides a publish-subscribe architecture for streaming E/I ratio data from FSL-MRS analysis to the visualization system. This approach offers several advantages over the previous TCP-based system:

- **Standardized Protocol**: LSL is a widely-used standard in neuroscience research
- **Better Reliability**: Built-in buffering and error handling
- **Scalability**: Multiple consumers can subscribe to the same data stream
- **Metadata Support**: Rich metadata about the data stream
- **Cross-Platform**: Works across different operating systems and programming languages

## Architecture

```
FSL-MRS Analysis → LSL Publisher → LSL Network → LSL Receiver → TCP Forwarder → PsychoPy Visualization
```

### Components

1. **FSL-MRS LSL Publisher** (`fsl_mrs_lsl_publisher.py`)
   - Performs FSL-MRS analysis (or simulation)
   - Publishes E/I ratio data to LSL stream
   - Configurable sampling rate and parameters

2. **LSL E/I Receiver** (`lsl_ei_receiver.py`)
   - Subscribes to FSL-MRS LSL stream
   - Forwards data to existing TCP-based visualization
   - Acts as a bridge between LSL and existing system

3. **PsychoPy Display Manager** (unchanged)
   - Receives data via existing TCP interface
   - Displays real-time E/I ratio visualization

## Installation

### Prerequisites

1. **Python 3.8+**: Ensure you have Python 3.8 or later installed
2. **Poetry**: Install Poetry for dependency management:
   ```bash
   curl -sSL https://install.python-poetry.org | python3 -
   ```

### Dependencies

Install all dependencies using Poetry:

```bash
# Install core dependencies
poetry install

# Install with FSL-MRS support (optional)
poetry install --extras fsl-mrs
```

If you want to add dependencies manually:

```bash
poetry add pylsl numpy scipy matplotlib pandas
poetry add fsl-mrs  # Optional, for real FSL-MRS integration
```

### LSL Library

The Lab Streaming Layer library may need to be installed separately on some systems:

- **macOS**: `brew install labstreaminglayer/tap/lsl`
- **Ubuntu/Debian**: Download from [LSL releases](https://github.com/sccn/liblsl/releases)
- **Windows**: Download from [LSL releases](https://github.com/sccn/liblsl/releases)

## Configuration

The LSL system is configured via `config.yaml`:

```yaml
# FSL-MRS LSL Configuration
fsl_mrs_lsl:
  stream_name: 'FSL-MRS-EI-Ratio'
  stream_type: 'EI_Ratio'
  source_id: 'fsl-mrs-ei-001'
  sampling_rate: 1.0  # Hz
  simulation_mode: true  # Set to false when using real FSL-MRS
  simulation_range: [0.3, 1.2]  # Min/max E/I ratio values
  simulation_noise: 0.05  # Noise level for simulation

# FSL-MRS Configuration
fsl_mrs:
  data_path: null  # Path to MRS data files
  basis_set_path: null  # Path to basis set files
  fitting_params:
    # FSL-MRS fitting parameters would go here

# LSL E/I Receiver Configuration
lsl_ei_receiver:
  stream_name: 'FSL-MRS-EI-Ratio'
  stream_type: 'EI_Ratio'
  source_id: null  # null means any source
  forward_host: '127.0.0.1'
  forward_port: 5005
  forward_enabled: true
  connection_retry_interval: 5.0  # seconds
  stream_resolve_timeout: 5.0  # seconds
  buffer_length: 360  # seconds
  max_chunk_length: 0  # 0 = no chunking
```

## Usage

### Running the LSL-based E/I Visualization

1. Start the main menu system:
   ```bash
   poetry run python menu.py
   ```

2. Select "FSL-MRS E/I Visualization (LSL)" from the menu

3. The system will automatically:
   - Start the FSL-MRS LSL publisher
   - Start the LSL receiver
   - Begin visualization in PsychoPy

### Manual Testing

Test the LSL system independently using Poetry:

```bash
# Test the complete LSL pipeline
poetry run python test_lsl_system.py
# Or use the Poetry script:
poetry run test-lsl

# Test just the publisher
poetry run python fsl_mrs_lsl_publisher.py --simulation
# Or use the Poetry script:
poetry run fsl-mrs-publisher --simulation

# Test just the receiver (in another terminal)
poetry run python lsl_ei_receiver.py
# Or use the Poetry script:
poetry run lsl-receiver
```

### Poetry Scripts

The project includes convenient Poetry scripts defined in `pyproject.toml`:

- `poetry run realtime-mrs` - Start the main menu system
- `poetry run test-lsl` - Test the LSL system
- `poetry run fsl-mrs-publisher` - Run the FSL-MRS publisher
- `poetry run lsl-receiver` - Run the LSL receiver

### Using Real FSL-MRS Data

To use real FSL-MRS data instead of simulation:

1. Update `config.yaml`:
   ```yaml
   fsl_mrs_lsl:
     simulation_mode: false
   
   fsl_mrs:
     data_path: "/path/to/your/mrs/data"
     basis_set_path: "/path/to/basis/set"
   ```

2. Ensure FSL-MRS is properly installed and configured

3. Run the system as normal

## FSL-MRS Integration Details

### Data Processing Pipeline

The FSL-MRS LSL publisher implements the following pipeline:

1. **Data Loading**: Load MRS data using FSL-MRS I/O functions
2. **Preprocessing**: Apply standard preprocessing steps
3. **Fitting**: Fit metabolite spectra using FSL-MRS fitting algorithms
4. **E/I Calculation**: Calculate excitatory/inhibitory ratio from fitted metabolites
5. **Streaming**: Publish E/I ratio to LSL stream

### Metabolite Analysis

The E/I ratio is calculated from key metabolites:

- **Excitatory**: Glutamate (Glu), Glutamine (Gln)
- **Inhibitory**: GABA
- **Ratio**: (Glu + Gln) / GABA

### Real-time Considerations

- **Sampling Rate**: Configurable (default 1 Hz)
- **Latency**: Minimal buffering for real-time display
- **Error Handling**: Robust error handling for missing data or fitting failures

## Troubleshooting

### Common Issues

1. **LSL Stream Not Found**
   - Check that the publisher is running
   - Verify stream names match in config
   - Check firewall settings

2. **FSL-MRS Import Errors**
   - Ensure FSL-MRS is properly installed
   - Check Python environment and paths
   - Use simulation mode for testing

3. **Connection Issues**
   - Verify TCP port 5005 is available
   - Check network connectivity
   - Review firewall settings

### Debug Mode

Enable debug mode in `config.yaml`:

```yaml
fsl_mrs_lsl:
  debug_mode: true

lsl_ei_receiver:
  debug_mode: true
```

This will provide detailed logging of the LSL operations.

### Log Files

Check the following log files for debugging:

- `realtime_mrs.log`: Main application log
- Console output from publisher and receiver processes

## Performance Optimization

### For Real-time Use

1. **Reduce Processing Latency**:
   - Optimize FSL-MRS fitting parameters
   - Use appropriate basis sets
   - Consider parallel processing

2. **Network Optimization**:
   - Use local network for LSL streams
   - Minimize network hops
   - Consider dedicated network interface

3. **System Resources**:
   - Ensure adequate CPU and memory
   - Close unnecessary applications
   - Use SSD storage for data files

## Future Enhancements

Potential improvements to the LSL integration:

1. **Multiple Stream Support**: Support for multiple MRS data streams
2. **Advanced Metabolite Analysis**: Additional metabolite ratios and metrics
3. **Quality Metrics**: Real-time data quality assessment
4. **Adaptive Sampling**: Dynamic sampling rate based on data quality
5. **Cloud Integration**: Support for cloud-based FSL-MRS processing

## References

- [Lab Streaming Layer Documentation](https://labstreaminglayer.readthedocs.io/)
- [FSL-MRS Documentation](https://fsl-mrs.readthedocs.io/)
- [PsychoPy Documentation](https://psychopy.org/documentation.html)

## Support

For issues related to:
- **LSL Integration**: Check this documentation and log files
- **FSL-MRS**: Refer to FSL-MRS documentation and support channels
- **PsychoPy**: Refer to PsychoPy documentation and community forums 