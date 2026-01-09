#!/usr/bin/env python3
"""
Install script for SF Wizard dependencies
Manages required packages with size estimation
"""

import subprocess
import sys
import json
import re

# Do not pin versions by default: allow pip to choose compatible versions.
DEPENDENCIES = {
    "openpyxl": None,  # Excel file handling
    "et-xmlfile": None,  # Required by openpyxl
}

def get_package_size(package_name):
    """
    Estimate package download size using PyPI JSON API
    Returns size in MB or None if unavailable
    """
    try:
        import urllib.request
        url = f"https://pypi.org/pypi/{package_name}/json"
        with urllib.request.urlopen(url, timeout=5) as response:
            data = json.loads(response.read().decode())
            
        total_size = 0
        for release in data.get("releases", {}).values():
            for file_info in release:
                total_size += file_info.get("size", 0)
        
        return total_size / (1024 * 1024) if total_size else None
    except Exception:
        return None

def format_size(mb):
    """Format size in MB to human readable format"""
    if mb < 1:
        return f"{mb * 1024:.1f} KB"
    elif mb < 1024:
        return f"{mb:.1f} MB"
    else:
        return f"{mb / 1024:.1f} GB"

def get_total_size_estimate():
    """Get total estimated download size"""
    total = 0
    sizes = {}
    
    print("Fetching package sizes from PyPI...")
    for package, version in DEPENDENCIES.items():
        # When no version is provided, estimate using the latest release only
        size = get_package_size(package)
        sizes[package] = size
        if size:
            total += size
            print(f"  {package}: {format_size(size)}")
        else:
            print(f"  {package}: size unavailable")
    
    return total, sizes

def install_dependencies():
    """Install all dependencies"""
    print("\n" + "="*50)
    print("Getting package information...")
    print("="*50)
    
    total_size, sizes = get_total_size_estimate()
    
    print("\n" + "="*50)
    print("Installation Summary")
    print("="*50)
    print(f"\nPackages to install: {len(DEPENDENCIES)}")
    for package, version in DEPENDENCIES.items():
        print(f"  • {package} ({version})")
    
    if total_size:
        print(f"\nEstimated download size: {format_size(total_size)}")
    
    response = input("\nProceed with installation? (Y/N): ").strip().upper()
    
    if response != "Y":
        print("Installation cancelled.")
        return False
    
    print("\n" + "="*50)
    print("Installing packages...")
    print("="*50 + "\n")
    
    packages_to_install = []
    for pkg, version in DEPENDENCIES.items():
        if version:
            packages_to_install.append(f"{pkg}=={version}")
        else:
            packages_to_install.append(pkg)
    
    try:
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "--upgrade", "pip"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        
        result = subprocess.call(
            [sys.executable, "-m", "pip", "install"] + packages_to_install
        )
        
        if result == 0:
            print("\n" + "="*50)
            print("Installation completed successfully!")
            print("="*50)
            
            # Get actual installed sizes (approximate)
            try:
                result = subprocess.run(
                    [sys.executable, "-m", "pip", "show"] + packages_to_install,
                    capture_output=True,
                    text=True,
                )
                print(f"\nInstalled packages (summary):")
                for pkg in packages_to_install:
                    print(f"  ✓ {pkg}")
            except Exception:
                pass
            
            return True
        else:
            print("\nInstallation failed. Please check the error messages above.")
            return False
            
    except Exception as e:
        print(f"Error during installation: {e}")
        return False

if __name__ == "__main__":
    success = install_dependencies()
    sys.exit(0 if success else 1)
