#!/usr/bin/env python3
"""
Test LSL System
Simple test script to verify the FSL-MRS LSL publisher and receiver work correctly.
"""

import time
import subprocess
import threading
import signal
import sys
from logger import get_logger

logger = get_logger("LSL_Test")

def monitor_process(process, name):
    """Monitor process output."""
    try:
        for line in iter(process.stdout.readline, ''):
            if line.strip():
                print(f"[{name}] {line.strip()}")
    except Exception as e:
        logger.error(f"Error monitoring {name}: {e}")

def test_lsl_system():
    """Test the LSL publisher and receiver system."""
    print("Testing FSL-MRS LSL System...")
    print("=" * 50)
    
    publisher_process = None
    receiver_process = None
    
    try:
        # Start publisher
        print("Starting FSL-MRS LSL publisher...")
        publisher_process = subprocess.Popen(
            ["poetry", "run", "python", "fsl_mrs_lsl_publisher.py", "--simulation"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        # Monitor publisher
        pub_thread = threading.Thread(
            target=monitor_process,
            args=(publisher_process, "Publisher"),
            daemon=True
        )
        pub_thread.start()
        
        # Wait for publisher to start
        time.sleep(3)
        
        # Start receiver
        print("Starting LSL E/I receiver...")
        receiver_process = subprocess.Popen(
            ["poetry", "run", "python", "lsl_ei_receiver.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        # Monitor receiver
        rec_thread = threading.Thread(
            target=monitor_process,
            args=(receiver_process, "Receiver"),
            daemon=True
        )
        rec_thread.start()
        
        print("Both processes started. Running for 30 seconds...")
        print("You should see E/I ratio data being published and received.")
        print("Press Ctrl+C to stop early.")
        
        # Run for 30 seconds
        for i in range(30):
            if publisher_process.poll() is not None:
                print(f"Publisher exited with code {publisher_process.returncode}")
                break
            if receiver_process.poll() is not None:
                print(f"Receiver exited with code {receiver_process.returncode}")
                break
            time.sleep(1)
            if i % 5 == 0:
                print(f"Running... {30-i} seconds remaining")
        
        print("Test completed successfully!")
        
    except KeyboardInterrupt:
        print("\nTest interrupted by user.")
        
    except Exception as e:
        logger.error(f"Test error: {e}")
        
    finally:
        # Clean up
        if publisher_process and publisher_process.poll() is None:
            print("Terminating publisher...")
            publisher_process.terminate()
            try:
                publisher_process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                publisher_process.kill()
                
        if receiver_process and receiver_process.poll() is None:
            print("Terminating receiver...")
            receiver_process.terminate()
            try:
                receiver_process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                receiver_process.kill()
        
        print("Test cleanup completed.")

if __name__ == "__main__":
    test_lsl_system() 