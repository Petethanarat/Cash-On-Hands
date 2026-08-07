# for /f "tokens=1 delims==" %%i in ('pip freeze') do (echo Upgrading %%i pip install --upgrade %%i)
import os
import sys
import subprocess

def is_venv():
    """Check if the script is running inside a virtual environment."""
    return hasattr(sys, 'real_prefix') or (sys.prefix != sys.base_prefix) or os.getenv('VIRTUAL_ENV') is not None

def get_installed_packages():
    """Returns a list of installed packages using 'pip freeze'."""
    result = subprocess.run([sys.executable, '-m', 'pip', 'freeze'], stdout=subprocess.PIPE)
    packages = result.stdout.decode('utf-8').splitlines()
    return [pkg.split('==')[0] for pkg in packages]  # Extract package name

def upgrade_package(package):
    """Upgrades a single package."""
    print(f"Upgrading {package}...")
    subprocess.run([sys.executable, '-m', 'pip', 'install', '--upgrade', package])

def update():
    if not is_venv():
        print("Error: This script is not running inside a virtual environment.")
        sys.exit(1)
    
    packages = get_installed_packages()
    
    if not packages:
        print("No packages found to upgrade.")
        return
    
    for package in packages:
        upgrade_package(package)

if __name__ == '__main__':
    update()
