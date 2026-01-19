#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test runner for GGU QGIS Tools.

Usage:
    python run_tests.py              # Run unit tests only
    python run_tests.py --integration  # Include integration tests
    python run_tests.py --qgis         # Run in QGIS Python environment
"""

import os
import sys
import unittest
import argparse


def run_unit_tests():
    """Run unit tests that don't require QGIS."""
    # Discover and run tests
    loader = unittest.TestLoader()
    suite = loader.discover("tests", pattern="test_*.py")

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return 0 if result.wasSuccessful() else 1


def main():
    parser = argparse.ArgumentParser(description="Run GGU QGIS Tools tests")
    parser.add_argument(
        "--integration",
        action="store_true",
        help="Include integration tests (requires CLI executable)",
    )
    parser.add_argument(
        "--qgis",
        action="store_true",
        help="Run tests requiring QGIS (must be run from QGIS Python console)",
    )
    args = parser.parse_args()

    # Set environment for integration tests
    if args.integration:
        os.environ["RUN_INTEGRATION_TESTS"] = "1"

    return run_unit_tests()


if __name__ == "__main__":
    sys.exit(main())
