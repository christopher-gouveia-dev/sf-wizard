#!/usr/bin/env python3
"""
Quick start script for SF Wizard
Guides user through first-time setup
"""

import os
import sys
import subprocess
from pathlib import Path


def check_dependencies():
    """Check if required dependencies are installed"""
    try:
        import openpyxl
        print("✓ openpyxl is installed")
        return True
    except ImportError:
        print("✗ openpyxl is not installed")
        return False


def main():
    print("="*50)
    print("SF Wizard - Quick Start")
    print("="*50 + "\n")
    
    # Check if dependencies are installed
    print("Checking dependencies...")
    if not check_dependencies():
        print("\nDependencies not found. Running installer...\n")
        result = subprocess.call([sys.executable, "install.py"])
        if result != 0:
            print("\nInstallation failed. Please run 'python install.py' manually.")
            sys.exit(1)
    
    print("\n✓ All dependencies are available!\n")
    
    # Create excel-files directory if it doesn't exist
    excel_dir = Path("excel-files")
    if not excel_dir.exists():
        excel_dir.mkdir()
        print(f"✓ Created {excel_dir}/ directory\n")
    
    print("="*50)
    print("Starting SF Wizard Server...")
    print("="*50)
    print("\nServer will run at: http://localhost:8000")
    print("Press Ctrl+C to stop\n")
    
    # Start the server
    try:
        subprocess.call([sys.executable, "app.py"])
    except KeyboardInterrupt:
        print("\n\nServer stopped.")
        sys.exit(0)


if __name__ == "__main__":
    main()
