import os
from pathlib import Path
import re
from datetime import datetime
import subprocess
import sys
def increment_version(version):
    parts = list(map(int, version.split(".")))
    parts[-1] += 1
    return ".".join(map(str, parts))

def get_datetime():
    return datetime.now().strftime("%Y-%m-%d-%H:%M")

def read_version(file_path):
    if not file_path.exists():
        print("⚠️ Version file not found. Creating `__version__.py` with default version (1.0.0).")
        timestamp = get_datetime()
        file_path.write_text(
            f'__version__ = "1.0.0"\n'
            f'"{timestamp} - 1.0.0 = Version initialized"\n'
        )
        return "1.0.0"
    
    with open(file_path, "r") as f:
        content = f.read()
        match = re.search(r'__version__ = "(.+)"', content)
        if match:
            return match.group(1)
        raise ValueError("Version not found in file.")

def write_version(file_path, version,version_message):
    with open(file_path, "r") as f:
        content = f.readlines()
    with open(file_path, "w") as f:
        for line in content:
            if re.match(r'__version__ = ".*"', line):
                timestamp = get_datetime()
                f.write(f'__version__ = "{version}"\n' + f'"{timestamp} - {version} = {version_message}"\n')
            else:
                f.write(line)

def get_version(path,version_message):
    version_file = Path(path+ "__version__.py")
    print(version_file)
    current_version = read_version(version_file)
    print(f"Current version: {current_version}")

    new_version = increment_version(current_version)
    print(f"New version: {new_version}")

    write_version(version_file, new_version,version_message)
    return new_version

def ensure_pyinstaller():
    try:
        import PyInstaller  # Try to import PyInstaller
    except ImportError:
        print("⚠️ PyInstaller not found. Installing in virtual environment...")
        subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], check=True)
        print("✅ PyInstaller installed successfully in venv!")

def venv_path():
    return os.getenv("VIRTUAL_ENV")  # Get active venv path

def create_exe(python_file='main.py',exe_name ='main',hidden_import=None,version_message='Message Added !!!'):
    if not (VENV_PATH := venv_path()):
        raise EnvironmentError("This function must be run within a virtual environment.")
    
    ensure_pyinstaller()  # Call the function before running PyInstaller

    PROCESS_PATH = str(Path(VENV_PATH).parent)
    SOURCE_PATH = PROCESS_PATH + '\src\\'
    DEPLOY_PATH = SOURCE_PATH + '\deploy\\'
    ICON_FILE = SOURCE_PATH + 'deploy\\di.ico'
    
    version = get_version(DEPLOY_PATH,version_message)

    import PyInstaller.__main__
    PyInstaller.__main__.run([
        f"{SOURCE_PATH}{python_file}",
        "--onefile",
        "--console",
        "--clean",
        f"--hidden-import={hidden_import}",
        f"--icon={ICON_FILE}",
        f"--name={exe_name}_v{version}"
    ])

if __name__ == '__main__':
    # pyinstaller --onefile --hidden-import=win32timezone --icon=deploy\di.ico --name=DI_XXX --clean test.py
    create_exe( python_file     ='main.py',
                exe_name        ='DS008',
                # hidden_import   ='win32timezone',
                version_message = 'Edit add row process!!!!!!!'
    )




