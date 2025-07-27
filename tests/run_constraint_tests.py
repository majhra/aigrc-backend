#!/usr/bin/env python3
"""
Test runner for database constraint and foreign key validation tests.

This script runs all the constraint-related tests to catch database integrity
issues before they reach production. It should be integrated into CI/CD pipelines.

Usage:
    python tests/run_constraint_tests.py
    python tests/run_constraint_tests.py --verbose
    python tests/run_constraint_tests.py --xml-output=test-results.xml
"""

import sys
import unittest
import argparse
from io import StringIO
import xml.etree.ElementTree as ET
from datetime import datetime

def run_constraint_tests(verbose=False, xml_output=None):
    """Run all constraint-related tests."""
    
    # Import all constraint test modules
    test_modules = [
        'tests.modules.test_foreign_key_constraints',
        'tests.modules.test_cascade_deletion_scenarios', 
        'tests.modules.test_database_constraints'
    ]
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    for module_name in test_modules:
        try:
            module = __import__(module_name, fromlist=[''])
            module_suite = loader.loadTestsFromModule(module)
            suite.addTests(module_suite)
            print(f"✓ Loaded tests from {module_name}")
        except ImportError as e:
            print(f"✗ Failed to import {module_name}: {e}")
            return False
    
    # Configure test runner
    stream = StringIO() if xml_output else sys.stdout
    runner = unittest.TextTestRunner(
        stream=stream,
        verbosity=2 if verbose else 1,
        buffer=True,
        failfast=False
    )
    
    print(f"\n🔧 Running {suite.countTestCases()} constraint validation tests...\n")
    
    # Run tests
    start_time = datetime.now()
    result = runner.run(suite)
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    # Print summary
    print(f"\n📊 Test Results Summary:")
    print(f"   Tests run: {result.testsRun}")
    print(f"   Failures: {len(result.failures)}")
    print(f"   Errors: {len(result.errors)}")
    print(f"   Skipped: {len(result.skipped) if hasattr(result, 'skipped') else 0}")
    print(f"   Duration: {duration:.2f} seconds")
    
    # Print failure details
    if result.failures:
        print(f"\n❌ Failures ({len(result.failures)}):")
        for test, traceback in result.failures:
            print(f"   - {test}: {traceback.split(chr(10))[-2] if chr(10) in traceback else traceback}")
    
    if result.errors:
        print(f"\n💥 Errors ({len(result.errors)}):")
        for test, traceback in result.errors:
            print(f"   - {test}: {traceback.split(chr(10))[-2] if chr(10) in traceback else traceback}")
    
    # Generate XML output if requested
    if xml_output:
        generate_xml_report(result, suite, duration, xml_output, stream.getvalue())
    
    # Determine success
    success = len(result.failures) == 0 and len(result.errors) == 0
    
    if success:
        print(f"\n✅ All constraint tests passed! Database integrity checks are working correctly.")
        print(f"🛡️  Foreign key constraint violations should be caught before production.")
    else:
        print(f"\n❌ Some constraint tests failed. Database integrity issues may not be caught.")
        print(f"🚨 Review the failures above to ensure proper constraint handling.")
    
    return success

def generate_xml_report(result, suite, duration, xml_output, test_output):
    """Generate JUnit-style XML report for CI/CD integration."""
    
    root = ET.Element("testsuite")
    root.set("name", "constraint-tests")
    root.set("tests", str(result.testsRun))
    root.set("failures", str(len(result.failures)))
    root.set("errors", str(len(result.errors)))
    root.set("time", f"{duration:.3f}")
    root.set("timestamp", datetime.now().isoformat())
    
    # Add system output
    system_out = ET.SubElement(root, "system-out")
    system_out.text = test_output
    
    # Add test cases
    test_index = 0
    for test_case in suite:
        if hasattr(test_case, '_testMethodName'):
            testcase = ET.SubElement(root, "testcase")
            testcase.set("classname", f"{test_case.__class__.__module__}.{test_case.__class__.__name__}")
            testcase.set("name", test_case._testMethodName)
            testcase.set("time", "0.0")  # Individual test times not available
            
            # Check if this test failed or had an error
            test_id = f"{test_case.__class__.__name__}.{test_case._testMethodName}"
            
            for test, traceback in result.failures:
                if test_id in str(test):
                    failure = ET.SubElement(testcase, "failure")
                    failure.set("message", "Test failed")
                    failure.text = traceback
                    break
            
            for test, traceback in result.errors:
                if test_id in str(test):
                    error = ET.SubElement(testcase, "error")
                    error.set("message", "Test error")
                    error.text = traceback
                    break
        
        elif hasattr(test_case, '__iter__'):
            # Handle test suites
            for sub_test in test_case:
                if hasattr(sub_test, '_testMethodName'):
                    testcase = ET.SubElement(root, "testcase")
                    testcase.set("classname", f"{sub_test.__class__.__module__}.{sub_test.__class__.__name__}")
                    testcase.set("name", sub_test._testMethodName)
                    testcase.set("time", "0.0")
    
    # Write XML file
    tree = ET.ElementTree(root)
    tree.write(xml_output, encoding="utf-8", xml_declaration=True)
    print(f"\n📄 XML report written to: {xml_output}")

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Run database constraint validation tests")
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Run tests in verbose mode"
    )
    parser.add_argument(
        "--xml-output",
        metavar="FILE",
        help="Generate XML test report for CI/CD integration"
    )
    
    args = parser.parse_args()
    
    print("🧪 Database Constraint Test Runner")
    print("=" * 50)
    print("This test suite validates foreign key constraint handling")
    print("and ensures database integrity violations are caught early.")
    print("=" * 50)
    
    success = run_constraint_tests(verbose=args.verbose, xml_output=args.xml_output)
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()