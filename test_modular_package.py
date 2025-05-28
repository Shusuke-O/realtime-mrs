#!/usr/bin/env python3
"""
Test script to verify the modular realtime-mrs package works correctly.

This script tests the basic functionality of the modular package without
requiring external dependencies like PsychoPy or LSL.
"""

import sys
import traceback
from pathlib import Path

def test_imports():
    """Test that all core modules can be imported."""
    print("Testing imports...")
    
    try:
        # Test core imports
        from realtime_mrs.core import get_logger, load_config, ensure_data_dir
        from realtime_mrs.core.utils import Timer, ThreadSafeCounter
        print("✓ Core modules imported successfully")
        
        # Test task imports
        from realtime_mrs.tasks import BaseTask, TaskConfig, TaskResult
        print("✓ Task modules imported successfully")
        
        # Test main package import
        from realtime_mrs import __version__, get_logger as pkg_get_logger
        print(f"✓ Main package imported successfully (version: {__version__})")
        
        return True
        
    except ImportError as e:
        print(f"✗ Import failed: {e}")
        traceback.print_exc()
        return False

def test_logging():
    """Test logging functionality."""
    print("\nTesting logging...")
    
    try:
        from realtime_mrs.core import get_logger, setup_logging
        
        # Setup logging
        log_file = setup_logging(log_level="INFO")
        print(f"✓ Logging setup successful, log file: {log_file}")
        
        # Test logger creation
        logger = get_logger("test_module")
        logger.info("Test log message")
        print("✓ Logger created and message logged")
        
        return True
        
    except Exception as e:
        print(f"✗ Logging test failed: {e}")
        traceback.print_exc()
        return False

def test_configuration():
    """Test configuration functionality."""
    print("\nTesting configuration...")
    
    try:
        from realtime_mrs.core import load_config, get_config, set_config
        
        # Load default configuration
        config = load_config()
        print("✓ Default configuration loaded")
        
        # Test getting config values
        log_level = get_config('global.log_level', 'INFO')
        print(f"✓ Config value retrieved: global.log_level = {log_level}")
        
        # Test setting config values
        set_config('test.value', 'test_data')
        test_value = get_config('test.value')
        assert test_value == 'test_data'
        print("✓ Config value set and retrieved successfully")
        
        return True
        
    except Exception as e:
        print(f"✗ Configuration test failed: {e}")
        traceback.print_exc()
        return False

def test_utilities():
    """Test utility functions."""
    print("\nTesting utilities...")
    
    try:
        from realtime_mrs.core.utils import Timer, ThreadSafeCounter, ensure_data_dir
        
        # Test Timer
        timer = Timer()
        timer.start()
        import time
        time.sleep(0.1)
        elapsed = timer.stop()
        assert 0.05 < elapsed < 0.2  # Should be around 0.1 seconds
        print(f"✓ Timer works correctly: {elapsed:.3f}s")
        
        # Test ThreadSafeCounter
        counter = ThreadSafeCounter(10)
        assert counter.get() == 10
        counter.increment(5)
        assert counter.get() == 15
        print("✓ ThreadSafeCounter works correctly")
        
        # Test data directory creation
        data_dir = ensure_data_dir("test_data")
        assert data_dir.exists()
        print(f"✓ Data directory created: {data_dir}")
        
        return True
        
    except Exception as e:
        print(f"✗ Utilities test failed: {e}")
        traceback.print_exc()
        return False

def test_task_base():
    """Test base task functionality."""
    print("\nTesting base task...")
    
    try:
        from realtime_mrs.tasks import BaseTask, TaskConfig, TaskResult
        
        # Create a simple test task
        class TestTask(BaseTask):
            def setup(self, **kwargs):
                return True
            
            def run_trial(self, trial_number, **kwargs):
                return {
                    'trial_number': trial_number,
                    'test_data': f'trial_{trial_number}',
                }
            
            def cleanup(self):
                return True
            
            def get_trial_count(self):
                return 3
        
        # Create task configuration
        config = TaskConfig(
            task_name="test_task",
            participant_id="test_participant",
            session_id="test_session",
            task_params={'n_trials': 3}
        )
        
        # Run the task
        task = TestTask(config)
        result = task.run()
        
        # Verify results
        assert result.completed == True
        assert len(result.trial_data) == 3
        assert result.duration > 0
        print("✓ Base task functionality works correctly")
        
        return True
        
    except Exception as e:
        print(f"✗ Base task test failed: {e}")
        traceback.print_exc()
        return False

def test_cli_imports():
    """Test CLI module imports."""
    print("\nTesting CLI imports...")
    
    try:
        from realtime_mrs.cli import create_parser, get_version
        
        # Test parser creation
        parser = create_parser()
        print("✓ CLI parser created successfully")
        
        # Test version function
        version = get_version()
        print(f"✓ Version retrieved: {version}")
        
        return True
        
    except Exception as e:
        print(f"✗ CLI test failed: {e}")
        traceback.print_exc()
        return False

def test_optional_imports():
    """Test optional imports (LSL, PsychoPy, etc.)."""
    print("\nTesting optional imports...")
    
    # Test LSL imports (should handle missing pylsl gracefully)
    try:
        from realtime_mrs.lsl import FSLMRSLSLPublisher, LSLReceiver
        if FSLMRSLSLPublisher is None:
            print("⚠ LSL components not available (pylsl not installed)")
        else:
            print("✓ LSL components imported successfully")
    except Exception as e:
        print(f"⚠ LSL import issue (expected if pylsl not installed): {e}")
    
    # Test PsychoPy imports (should handle missing psychopy gracefully)
    try:
        from realtime_mrs.display import PsychoPyDisplayManager
        if PsychoPyDisplayManager is None:
            print("⚠ PsychoPy components not available (psychopy not installed)")
        else:
            print("✓ PsychoPy components imported successfully")
    except Exception as e:
        print(f"⚠ PsychoPy import issue (expected if psychopy not installed): {e}")
    
    return True

def main():
    """Run all tests."""
    print("=" * 60)
    print("REALTIME-MRS MODULAR PACKAGE TEST")
    print("=" * 60)
    
    tests = [
        test_imports,
        test_logging,
        test_configuration,
        test_utilities,
        test_task_base,
        test_cli_imports,
        test_optional_imports,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"✗ Test {test.__name__} crashed: {e}")
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"TEST RESULTS: {passed} passed, {failed} failed")
    print("=" * 60)
    
    if failed == 0:
        print("🎉 All tests passed! The modular package is working correctly.")
        return 0
    else:
        print("❌ Some tests failed. Check the output above for details.")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 