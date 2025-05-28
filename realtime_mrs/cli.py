"""
Command-line interface for the realtime-mrs package.

Provides easy access to package functionality through command-line commands.
"""

import argparse
import sys
from pathlib import Path
from typing import List, Optional

from .core.logger import setup_logging, get_logger
from .core.config import load_config, get_config
from .core.utils import check_dependencies, get_system_info

logger = get_logger(__name__)

def create_parser() -> argparse.ArgumentParser:
    """Create the main argument parser."""
    parser = argparse.ArgumentParser(
        prog='realtime-mrs',
        description='Real-time MRS visualization system with FSL-MRS and Lab Streaming Layer integration',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  realtime-mrs menu                    # Launch interactive menu
  realtime-mrs lsl-publisher           # Start LSL publisher
  realtime-mrs lsl-receiver            # Start LSL receiver
  realtime-mrs test-lsl               # Test LSL system
  realtime-mrs check-deps             # Check dependencies
  realtime-mrs config --show          # Show current configuration
        """
    )
    
    parser.add_argument(
        '--version',
        action='version',
        version=f'realtime-mrs {get_version()}'
    )
    
    parser.add_argument(
        '--config',
        type=str,
        help='Path to configuration file'
    )
    
    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
        default='INFO',
        help='Set logging level'
    )
    
    parser.add_argument(
        '--log-file',
        type=str,
        help='Path to log file'
    )
    
    # Subcommands
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Menu command
    menu_parser = subparsers.add_parser('menu', help='Launch interactive menu')
    
    # LSL commands
    lsl_parser = subparsers.add_parser('lsl-publisher', help='Start LSL publisher')
    lsl_parser.add_argument('--simulation', action='store_true', help='Use simulation mode')
    lsl_parser.add_argument('--rate', type=float, default=1.0, help='Sampling rate (Hz)')
    
    receiver_parser = subparsers.add_parser('lsl-receiver', help='Start LSL receiver')
    receiver_parser.add_argument('--stream-name', type=str, help='LSL stream name to connect to')
    
    # Test command
    test_parser = subparsers.add_parser('test-lsl', help='Test LSL system')
    test_parser.add_argument('--duration', type=float, default=10.0, help='Test duration (seconds)')
    
    # Task commands
    task_parser = subparsers.add_parser('task', help='Run a specific task')
    task_parser.add_argument('task_name', choices=['m1', 'v1', 'ei'], help='Task to run')
    task_parser.add_argument('--participant', type=str, default='test_participant', help='Participant ID')
    task_parser.add_argument('--session', type=str, default='session_001', help='Session ID')
    task_parser.add_argument('--trials', type=int, help='Number of trials')
    
    # Utility commands
    deps_parser = subparsers.add_parser('check-deps', help='Check dependencies')
    
    config_parser = subparsers.add_parser('config', help='Configuration management')
    config_parser.add_argument('--show', action='store_true', help='Show current configuration')
    config_parser.add_argument('--save', type=str, help='Save configuration to file')
    config_parser.add_argument('--set', nargs=2, metavar=('KEY', 'VALUE'), help='Set configuration value')
    
    info_parser = subparsers.add_parser('info', help='Show system information')
    
    return parser

def get_version() -> str:
    """Get package version."""
    try:
        from . import __version__
        return __version__
    except ImportError:
        return "unknown"

def cmd_menu(args):
    """Launch interactive menu."""
    try:
        from .menu import main as menu_main
        menu_main()
    except ImportError as e:
        logger.error(f"Failed to import menu module: {e}")
        logger.error("Make sure PsychoPy is installed: pip install psychopy")
        return 1
    except Exception as e:
        logger.error(f"Menu execution failed: {e}")
        return 1
    return 0

def cmd_lsl_publisher(args):
    """Start LSL publisher."""
    try:
        from .lsl.fsl_mrs_publisher import main as publisher_main
        
        # Override config with command line arguments
        if args.simulation:
            from .core.config import set_config
            set_config('fsl_mrs_lsl.simulation_mode', True)
        
        if args.rate != 1.0:
            from .core.config import set_config
            set_config('fsl_mrs_lsl.sampling_rate', args.rate)
        
        publisher_main()
    except ImportError as e:
        logger.error(f"Failed to import LSL publisher: {e}")
        logger.error("Make sure pylsl is installed: pip install pylsl")
        return 1
    except Exception as e:
        logger.error(f"LSL publisher failed: {e}")
        return 1
    return 0

def cmd_lsl_receiver(args):
    """Start LSL receiver."""
    try:
        from .lsl.receiver import main as receiver_main
        
        # Override config with command line arguments
        if args.stream_name:
            from .core.config import set_config
            set_config('lsl.stream_name', args.stream_name)
        
        receiver_main()
    except ImportError as e:
        logger.error(f"Failed to import LSL receiver: {e}")
        logger.error("Make sure pylsl is installed: pip install pylsl")
        return 1
    except Exception as e:
        logger.error(f"LSL receiver failed: {e}")
        return 1
    return 0

def cmd_test_lsl(args):
    """Test LSL system."""
    try:
        from .testing.test_lsl_system import main as test_main
        test_main(duration=args.duration)
    except ImportError as e:
        logger.error(f"Failed to import LSL test module: {e}")
        logger.error("Make sure pylsl is installed: pip install pylsl")
        return 1
    except Exception as e:
        logger.error(f"LSL test failed: {e}")
        return 1
    return 0

def cmd_task(args):
    """Run a specific task."""
    try:
        from .tasks.base import TaskConfig
        
        # Create task config
        config = TaskConfig(
            task_name=f"{args.task_name}_task",
            participant_id=args.participant,
            session_id=args.session,
        )
        
        if args.trials:
            config.task_params['n_trials'] = args.trials
        
        # Import and run the appropriate task
        if args.task_name == 'm1':
            from .tasks.m1_tapping import M1TappingTask
            task = M1TappingTask(config)
        elif args.task_name == 'v1':
            from .tasks.v1_orientation import V1OrientationTask
            task = V1OrientationTask(config)
        elif args.task_name == 'ei':
            from .tasks.ei_visualization import EIVisualizationTask
            task = EIVisualizationTask(config)
        else:
            logger.error(f"Unknown task: {args.task_name}")
            return 1
        
        # Run the task
        result = task.run()
        
        if result.completed:
            logger.info(f"Task completed successfully. Duration: {result.duration:.1f}s")
        elif result.aborted:
            logger.warning("Task was aborted")
        else:
            logger.error(f"Task failed: {result.error}")
            return 1
            
    except ImportError as e:
        logger.error(f"Failed to import task module: {e}")
        return 1
    except Exception as e:
        logger.error(f"Task execution failed: {e}")
        return 1
    return 0

def cmd_check_deps(args):
    """Check dependencies."""
    dependencies = [
        'numpy',
        'scipy',
        'matplotlib',
        'pandas',
        'yaml',
        'pylsl',
        'psychopy',
        'pygame',
        'seaborn',
    ]
    
    results = check_dependencies(dependencies)
    
    print("Dependency Check Results:")
    print("=" * 40)
    
    for dep, available in results.items():
        status = "✓ Available" if available else "✗ Missing"
        print(f"{dep:15} {status}")
    
    missing = [dep for dep, available in results.items() if not available]
    
    if missing:
        print(f"\nMissing dependencies: {', '.join(missing)}")
        print("\nTo install missing dependencies:")
        print("pip install " + " ".join(missing))
        return 1
    else:
        print("\nAll dependencies are available!")
        return 0

def cmd_config(args):
    """Configuration management."""
    config = load_config(args.config if hasattr(args, 'config') else None)
    
    if args.show:
        import yaml
        print("Current Configuration:")
        print("=" * 40)
        print(yaml.dump(config, default_flow_style=False, indent=2))
    
    if args.set:
        key, value = args.set
        from .core.config import set_config
        
        # Try to convert value to appropriate type
        try:
            if value.lower() in ('true', 'false'):
                value = value.lower() == 'true'
            elif value.isdigit():
                value = int(value)
            elif '.' in value and value.replace('.', '').isdigit():
                value = float(value)
        except:
            pass  # Keep as string
        
        set_config(key, value)
        print(f"Set {key} = {value}")
    
    if args.save:
        from .core.config import save_config
        save_config(args.save)
        print(f"Configuration saved to {args.save}")
    
    return 0

def cmd_info(args):
    """Show system information."""
    info = get_system_info()
    
    print("System Information:")
    print("=" * 40)
    for key, value in info.items():
        print(f"{key:15} {value}")
    
    # Show package version
    print(f"{'package':15} realtime-mrs {get_version()}")
    
    return 0

def main(argv: Optional[List[str]] = None) -> int:
    """
    Main entry point for the CLI.
    
    Args:
        argv: Command line arguments (defaults to sys.argv)
        
    Returns:
        Exit code (0 for success, non-zero for error)
    """
    parser = create_parser()
    args = parser.parse_args(argv)
    
    # Setup logging
    setup_logging(
        log_file=args.log_file,
        log_level=args.log_level,
    )
    
    # Load configuration
    if args.config:
        load_config(args.config)
    
    # Execute command
    if args.command == 'menu':
        return cmd_menu(args)
    elif args.command == 'lsl-publisher':
        return cmd_lsl_publisher(args)
    elif args.command == 'lsl-receiver':
        return cmd_lsl_receiver(args)
    elif args.command == 'test-lsl':
        return cmd_test_lsl(args)
    elif args.command == 'task':
        return cmd_task(args)
    elif args.command == 'check-deps':
        return cmd_check_deps(args)
    elif args.command == 'config':
        return cmd_config(args)
    elif args.command == 'info':
        return cmd_info(args)
    else:
        parser.print_help()
        return 1

if __name__ == '__main__':
    sys.exit(main()) 