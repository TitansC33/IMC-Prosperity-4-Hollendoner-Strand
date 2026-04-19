"""
Master Test Runner - Executes all 3 tests in sequence with file logging

Tests run:
1. Position Limits Quick Test (20 iterations, ~4 min)
2. Position Limits Full Test (100 iterations, ~20 min)
3. EMA Variations Test (100 iterations per combo, ~40 min)

All results saved to files in current directory with timestamps.

Usage:
    python run_all_tests.py              # Run all 3 tests
    python run_all_tests.py --test1     # Run only test 1
    python run_all_tests.py --test2     # Run only test 2
    python run_all_tests.py --test3     # Run only test 3
"""

import sys
from pathlib import Path
import subprocess
import time
from datetime import datetime
import os

def run_test(test_num, test_name, cmd, output_file):
    """Run a single test and log output to file"""

    print(f"\n{'='*120}")
    print(f"TEST {test_num}: {test_name}")
    print(f"{'='*120}")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Output file: {output_file}")
    print(f"Command: {' '.join(cmd)}")
    print(f"{'='*120}\n")

    # Run command and write to file
    with open(output_file, 'w') as f:
        f.write(f"TEST {test_num}: {test_name}\n")
        f.write(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Command: {' '.join(cmd)}\n")
        f.write("=" * 120 + "\n\n")

    start_time = time.time()

    try:
        result = subprocess.run(
            cmd,
            cwd=Path(__file__).parent,
            capture_output=True,
            text=True,
            timeout=3600  # 1 hour timeout
        )

        # Write stdout
        with open(output_file, 'a') as f:
            f.write(result.stdout)
            if result.stderr:
                f.write("\n\nSTDERR:\n")
                f.write(result.stderr)

        elapsed = time.time() - start_time
        completion_msg = f"[PASS] COMPLETED in {elapsed:.1f}s ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})"

        print(completion_msg)
        with open(output_file, 'a') as f:
            f.write(f"\n{completion_msg}\n")

        return True

    except subprocess.TimeoutExpired:
        error_msg = f"[FAIL] TIMEOUT after 1 hour"
        print(error_msg)
        with open(output_file, 'a') as f:
            f.write(f"\n{error_msg}\n")
        return False

    except Exception as e:
        error_msg = f"[FAIL] ERROR: {str(e)}"
        print(error_msg)
        with open(output_file, 'a') as f:
            f.write(f"\n{error_msg}\n")
        return False


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Run all 3 comprehensive tests")
    parser.add_argument("--test1", action="store_true", help="Run only test 1 (position limits quick)")
    parser.add_argument("--test2", action="store_true", help="Run only test 2 (position limits full)")
    parser.add_argument("--test3", action="store_true", help="Run only test 3 (EMA variations)")
    parser.add_argument("--skip1", action="store_true", help="Skip test 1")
    parser.add_argument("--skip2", action="store_true", help="Skip test 2")
    parser.add_argument("--skip3", action="store_true", help="Skip test 3")

    args = parser.parse_args()

    # Determine which tests to run
    run_test1 = not args.skip1 and (not args.test2 and not args.test3 or args.test1)
    run_test2 = not args.skip2 and (not args.test1 and not args.test3 or args.test2)
    run_test3 = not args.skip3 and (not args.test1 and not args.test2 or args.test3)

    if not (run_test1 or run_test2 or run_test3):
        run_test1 = run_test2 = run_test3 = True

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    tests = []

    if run_test1:
        output_file = f"test1_positions_quick_{timestamp}.txt"
        tests.append({
            "num": 1,
            "name": "Position Limits - Quick Test (20 iterations)",
            "cmd": ["python", "run_comprehensive_testing.py", "--quick"],
            "output": output_file,
            "time": "~4 minutes"
        })

    if run_test2:
        output_file = f"test2_positions_full_{timestamp}.txt"
        tests.append({
            "num": 2,
            "name": "Position Limits - Full Test (100 iterations)",
            "cmd": ["python", "run_comprehensive_testing.py"],
            "output": output_file,
            "time": "~20 minutes"
        })

    if run_test3:
        output_file = f"test3_ema_variations_{timestamp}.txt"
        tests.append({
            "num": 3,
            "name": "EMA Variations - Grid Test (100 iterations per combo)",
            "cmd": ["python", "run_parameter_grid_search.py", "--test-ema"],
            "output": output_file,
            "time": "~40 minutes"
        })

    # Summary header
    print("\n" + "=" * 120)
    print("MASTER TEST RUNNER - COMPREHENSIVE PARAMETER OPTIMIZATION")
    print("=" * 120)
    print(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"\nTests to Run ({len(tests)}):")

    total_est_time = 0
    for test in tests:
        print(f"\n  [{test['num']}] {test['name']}")
        print(f"      Estimated: {test['time']}")
        print(f"      Output: {test['output']}")

    print(f"\n  Total Estimated Time: ~65 minutes (1 hour 5 min)")
    print(f"\n  Results saved to current directory:")
    print(f"  {Path(__file__).parent}")
    print("\n" + "=" * 120)

    # Run tests sequentially
    results = []
    for i, test in enumerate(tests, 1):
        print(f"\n[TEST {i}/{len(tests)}] Running: {test['name']}")

        success = run_test(
            test["num"],
            test["name"],
            test["cmd"],
            test["output"]
        )

        results.append({
            "test": test["name"],
            "output": test["output"],
            "success": success
        })

        if i < len(tests):
            print(f"\n[WAIT] Next test starting in 5 seconds...")
            time.sleep(5)

    # Final summary
    print("\n" + "=" * 120)
    print("ALL TESTS COMPLETED")
    print("=" * 120)
    print(f"End Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"\nResults Summary:")

    all_passed = True
    for result in results:
        status = "[PASS]" if result["success"] else "[FAIL]"
        print(f"  {status}: {result['test']}")
        print(f"         Output: {result['output']}")
        if not result["success"]:
            all_passed = False

    print(f"\nOverall Status: {'[PASS] ALL PASSED' if all_passed else '[FAIL] SOME FAILED'}")

    print("\nTo view results:")
    print(f"   cd {Path(__file__).parent}")
    print(f"   ls -lt test*.txt              # List all test outputs")
    print(f"   tail -100 test1_*.txt         # View last 100 lines of test 1")
    print(f"   grep -i best test*.txt        # Find best results across all tests")

    print("\n" + "=" * 120 + "\n")


if __name__ == "__main__":
    main()
