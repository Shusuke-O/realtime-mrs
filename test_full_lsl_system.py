#!/usr/bin/env python3
"""
Comprehensive LSL System Test
Tests the complete data acquisition and recording system.
"""

import time
import threading
from experiment_data_recorder import get_experiment_recorder, log_experiment_event
from task_lsl_publishers import get_m1_publisher, get_v1_publisher, get_physio_publisher
from data_analysis import ExperimentDataAnalyzer

def test_full_lsl_system():
    """Test the complete LSL data acquisition and recording system."""
    print("=" * 60)
    print("COMPREHENSIVE LSL SYSTEM TEST")
    print("=" * 60)
    
    # Get recorder and publishers
    recorder = get_experiment_recorder()
    m1_pub = get_m1_publisher()
    v1_pub = get_v1_publisher()
    physio_pub = get_physio_publisher()
    
    try:
        # 1. Start experiment session
        print("\n1. Starting experiment session...")
        session = recorder.start_session(
            participant_id="TEST_P001",
            session_id="comprehensive_test",
            experiment_name="lsl_system_test"
        )
        print(f"   ✓ Session started: {session.participant_id}/{session.session_id}")
        print(f"   ✓ Data directory: {session.data_directory}")
        
        # 2. Start recording
        print("\n2. Starting data recording...")
        if recorder.start_recording():
            print("   ✓ Recording started successfully")
            status = recorder.get_session_status()
            print(f"   ✓ Recording {len(status['recorded_streams'])} streams: {status['recorded_streams']}")
        else:
            print("   ✗ Failed to start recording")
            return False
        
        # 3. Simulate experiment events
        print("\n3. Simulating experiment events...")
        
        # Session start event
        log_experiment_event('session_start', 'experiment', {
            'participant_id': session.participant_id,
            'session_id': session.session_id,
            'test_type': 'comprehensive_lsl_test'
        })
        
        # M1 tapping task simulation
        print("   → Simulating M1 tapping task...")
        for trial in range(1, 4):  # 3 trials
            m1_pub.trial_start(trial, ['1', '2', '3', '4'])
            log_experiment_event('trial_start', 'm1_tapping', {'trial_number': trial})
            
            time.sleep(0.5)
            
            m1_pub.sequence_start(trial, ['1', '2', '3', '4'])
            
            # Simulate taps
            for pos, key in enumerate(['1', '2', '3', '4']):
                time.sleep(0.2)
                reaction_time = 0.2 + (pos * 0.05)  # Increasing RT
                is_correct = pos < 3  # First 3 correct, last one wrong
                pressed_key = key if is_correct else '1'  # Wrong key for last tap
                
                m1_pub.tap_event(trial, pos, key, pressed_key, reaction_time, is_correct)
                log_experiment_event('tap', 'm1_tapping', {
                    'trial_number': trial,
                    'sequence_position': pos,
                    'target_key': key,
                    'pressed_key': pressed_key,
                    'reaction_time': reaction_time,
                    'is_correct': is_correct
                })
            
            m1_pub.sequence_end(trial)
            m1_pub.trial_end(trial)
            log_experiment_event('trial_end', 'm1_tapping', {'trial_number': trial})
            
            time.sleep(0.3)
        
        # V1 orientation task simulation
        print("   → Simulating V1 orientation task...")
        for trial in range(1, 4):  # 3 trials
            v1_pub.trial_start(trial)
            log_experiment_event('trial_start', 'v1_orientation', {'trial_number': trial})
            
            time.sleep(0.3)
            
            orientation = 45.0 if trial % 2 == 1 else 135.0
            v1_pub.stimulus_on(trial, orientation, 0.1)
            log_experiment_event('stimulus_on', 'v1_orientation', {
                'trial_number': trial,
                'orientation': orientation,
                'duration': 0.1
            })
            
            time.sleep(0.1)
            
            v1_pub.stimulus_off(trial)
            log_experiment_event('stimulus_off', 'v1_orientation', {'trial_number': trial})
            
            time.sleep(0.4)
            
            # Simulate response
            reaction_time = 0.4 + (trial * 0.1)
            is_correct = trial <= 2  # First 2 correct, last one wrong
            response_key = 'left' if orientation == 45.0 else 'right'
            if not is_correct:
                response_key = 'right' if response_key == 'left' else 'left'
            
            v1_pub.response_event(trial, response_key, reaction_time, is_correct)
            log_experiment_event('response', 'v1_orientation', {
                'trial_number': trial,
                'response_key': response_key,
                'reaction_time': reaction_time,
                'is_correct': is_correct
            })
            
            v1_pub.trial_end(trial)
            log_experiment_event('trial_end', 'v1_orientation', {'trial_number': trial})
            
            time.sleep(0.2)
        
        # Physiological data simulation
        print("   → Simulating physiological data...")
        for i in range(10):
            physio_data = {
                'heart_rate': 72.0 + (i * 2),  # Increasing heart rate
                'eye_x': 512.0 + (i * 10),
                'eye_y': 384.0 + (i * 5),
                'pupil_diameter': 3.5 + (i * 0.1),
                'blink': 1.0 if i % 3 == 0 else 0.0  # Blink every 3rd sample
            }
            physio_pub.publish_sample(physio_data)
            time.sleep(0.1)
        
        # Intervention simulation
        print("   → Simulating intervention...")
        log_experiment_event('intervention_start', 'fsl_mrs', {
            'intervention_type': 'excitatory',
            'target_region': 'M1',
            'magnitude': 0.3
        })
        
        time.sleep(1.0)
        
        log_experiment_event('intervention_end', 'fsl_mrs', {
            'intervention_type': 'excitatory',
            'duration': 1.0
        })
        
        # Session end event
        log_experiment_event('session_end', 'experiment', {
            'total_duration': time.time() - session.start_time.timestamp()
        })
        
        print("   ✓ Event simulation completed")
        
        # 4. Stop recording
        print("\n4. Stopping data recording...")
        recorder.stop_recording()
        print("   ✓ Recording stopped")
        
        # 5. End session
        print("\n5. Ending experiment session...")
        recorder.end_session()
        print("   ✓ Session ended and data saved")
        
        # 6. Analyze recorded data
        print("\n6. Analyzing recorded data...")
        analyzer = ExperimentDataAnalyzer(session.data_directory)
        
        if analyzer.run_complete_analysis():
            print("   ✓ Data analysis completed successfully")
            
            # Show analysis results
            status = analyzer.get_session_status() if hasattr(analyzer, 'get_session_status') else {}
            if analyzer.analysis_results:
                print("\n   Analysis Summary:")
                
                # Task performance
                if 'task_performance' in analyzer.analysis_results:
                    task_perf = analyzer.analysis_results['task_performance']
                    
                    if 'm1_tapping' in task_perf:
                        m1_data = task_perf['m1_tapping']
                        print(f"   • M1 Tapping: {m1_data.get('total_taps', 0)} taps, "
                              f"{m1_data.get('accuracy', 0):.2f} accuracy, "
                              f"{m1_data.get('mean_reaction_time', 0):.3f}s mean RT")
                    
                    if 'v1_orientation' in task_perf:
                        v1_data = task_perf['v1_orientation']
                        print(f"   • V1 Orientation: {v1_data.get('total_responses', 0)} responses, "
                              f"{v1_data.get('accuracy', 0):.2f} accuracy, "
                              f"{v1_data.get('mean_reaction_time', 0):.3f}s mean RT")
                
                print(f"   • Analysis plots saved to: {session.data_directory}/analysis_plots/")
                print(f"   • Analysis report saved to: {session.data_directory}/analysis_report.json")
        else:
            print("   ✗ Data analysis failed")
        
        # 7. Cleanup publishers
        print("\n7. Cleaning up...")
        m1_pub.close()
        v1_pub.close()
        physio_pub.close()
        print("   ✓ Publishers closed")
        
        print("\n" + "=" * 60)
        print("✓ COMPREHENSIVE LSL SYSTEM TEST COMPLETED SUCCESSFULLY!")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        
        # Cleanup on error
        try:
            recorder.stop_recording()
            recorder.end_session()
            m1_pub.close()
            v1_pub.close()
            physio_pub.close()
        except:
            pass
        
        return False

if __name__ == "__main__":
    success = test_full_lsl_system()
    exit(0 if success else 1) 