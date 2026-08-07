import os
import subprocess
batch_script = r"""
@echo off
:: Create venv
:: Vscode Terminal select arrow down and choose "Select Default Profile > Command Prompt"
:: At terminal location ==> D:\Lightwork\Project\LH\Unsecured_Loan_Product\DI113_LMS\Workflow\Script\Python
:: run ===> py -m venv venv 
:: Vscode select ctlr+Shift+P to select "Interpreter" with "venv:venv" keyword
:: Make sure (venv) show up at Terminal 
:: At main.py terminal, run pip install polars rich 

:: After finising the programming, need to run upgrade all libraies and run the program to make sure it is working fine with latest libs
:: python.exe -m pip install --upgrade pip

:: D:\Lightwork\Project\LH\Unsecured_Loan_Product\DI113_LMS\Workflow\Script\Python> D:\Lightwork\Project\LH\Unsecured_Loan_Product\DI113_LMS\Workflow\Script\Python\pip freeze > requirements.txt
:: Create a file requirements.txt
:: pip freeze > requirements.txt

:: SET CORE_PYTHON_PATH=C:\Users\p6696\AppData\Local\Programs\Python\Python312
:: SET PROCESS_PATH=D:\Lightwork\Project\LH\Unsecured_Loan_Product\DI113_LMS\Workflow\Script\Python
:: SET VENV_PATH=%PROCESS_PATH%\venv

:: SET CORE_PYTHON_PATH=C:\Users\p6696\AppData\Local\Programs\Python\Python312
:: %%~d gets the drive.
:: %%~p gets the directory (path).
:: %%~i refers to the full result of the command.
:: for /f "delims=" %%i in ('py -c "import sys; print(sys.executable)"') do SET CORE_PYTHON_PATH=%%~dpi
:: SET CORE_PYTHON_PATH="%CORE_PYTHON_PATH:~0,-1%"
SET PY_LAUNCHER=PY
SET PROCESS_PATH={PROCESS_PATH}
SET VENV_PATH=%PROCESS_PATH%\venv
:: echo SET CORE_PYTHON_PATH = %CORE_PYTHON_PATH%
echo SET PY_LAUNCHER = %PY_LAUNCHER%
echo SET PROCESS_PATH = %PROCESS_PATH%
echo SET VENV_PATH = %VENV_PATH%

:: Check if Python is installed and available
:: C:\Users\p6696\AppData\Local\Programs\Python\Python312\python.exe --version
echo *****************************************************************************************************
echo Checking Python Version
:: %CORE_PYTHON_PATH%\python.exe --version
%PY_LAUNCHER% --version

IF ERRORLEVEL == 1 (
    echo *****************************************************************************************************
    echo Python is not installed or not added to PATH.
    exit /b 1
)

:: Create a virtual environment
:: C:\Users\p6696\AppData\Local\Programs\Python\Python312\python.exe -m venv %VENV_PATH%
:: C:\Users\p6696\AppData\Local\Programs\Python\Python312\python.exe -m venv D:\Lightwork\Project\LH\Unsecured_Loan_Product\DI113_LMS\Workflow\Script\Python\venv
echo *****************************************************************************************************
echo Setting-up VENV
:: %CORE_PYTHON_PATH%\python.exe -m venv %PROCESS_PATH%\venv
%PY_LAUNCHER% -m venv %PROCESS_PATH%\venv
IF ERRORLEVEL == 1 (
    echo *****************************************************************************************************
    echo VENV has been installed before
)

:: Activate the virtual environment
:: C:/Users/p6696/AppData/Local/Programs/Python/Python312/python.exe c:/Users/p6696/Desktop/Projects/py_demo/src/main.py
:: call c:\Users\p6696\Desktop\Projects\LHB_098\venv\Scripts\activate
echo *****************************************************************************************************
echo Activating VENV
call %VENV_PATH%\Scripts\activate

:: Step 1: Find pip and check if it's in a virtual environment
where pip | findstr /i "venv" >nul
IF %ERRORLEVEL% NEQ 0 (
    echo Not in a virtual environment or pip is under global env.
    exit /b 1
) ELSE (
    echo Pip is running from a virtual environment.
)

IF not EXIST %PROCESS_PATH%\requirements.txt (
    echo *****************************************************************************************************
    echo The program will not be run because requirements.txt is not existed. 
    deactivate
    exit /b 1
)

:: Step 2: Check if required libraries are installed
echo *****************************************************************************************************
echo Checking installed libraries...

setlocal enabledelayedexpansion
set libraries_missing=0
for /f "delims=" %%i in (%PROCESS_PATH%\requirements.txt) do (
    for /f "tokens=1 delims==" %%j in ("%%i") do (
        pip list | findstr /i "%%j" >nul 2>&1
        IF !ERRORLEVEL! == 1 (
            echo Library "%%j" is missing. pip will install this missing Library.
            set libraries_missing=1
            goto :breakLoop            
        )
    )
)

:breakLoop
IF !libraries_missing!==1 (
    echo Upgrading PIP
    echo *****************************************************************************************************
    python.exe -m pip install --upgrade pip

    echo *****************************************************************************************************
    echo Installing missing Libraies
    pip cache purge
    pip install -r %PROCESS_PATH%\requirements.txt
    findstr /i "playwright" %PROCESS_PATH%\requirements.txt >nul && (
        echo ***************************
        echo Playwright found in requirements.txt. Installing Playwright needed...
        playwright install
    ) || (
        echo ***************************
        echo Playwright not found in requirements.txt. Skipping Playwright installation.
    )
)
endlocal
echo *****************************************************************************************************
echo /////////////////////////////////////////////////////////////////////////////////////////////////////
echo \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
echo -----------------------------------------------------------------------------------------------------
echo                                      PYTHON-START-HERE                                        
echo -----------------------------------------------------------------------------------------------------
echo /////////////////////////////////////////////////////////////////////////////////////////////////////
echo \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
echo *****************************************************************************************************
echo Under VENV = %VIRTUAL_ENV%
IF "%VIRTUAL_ENV%" == "" (
    echo *****************************************************************************************************
    echo Virtual environment is not active. Exiting...
    exit /b 1
)
echo *****************************************************************************************************
echo Running the python script 
echo *****************************************************************************************************
%VENV_PATH%\Scripts\python.exe %PROCESS_PATH%\src\main.py
IF %ERRORLEVEL% NEQ 0 (
    echo Python script encountered a runtime error. Exit code: %ERRORLEVEL%
    deactivate
    exit /b %ERRORLEVEL%
) ELSE (
    echo Python script has completed successfully.
)

:: Deactivate the virtual environment
echo *****************************************************************************************************
echo De-activating VENV
deactivate
::pause
"""

# def get_batch_setup_location():
#     # CORE_PYTHON_PATH = sys.base_prefix
#     VENV_PATH = os.getenv('VIRTUAL_ENV')
#     if not VENV_PATH:
#         raise Exception("Must run under (venv) to create run.bat")
#     PROCESS_PATH = str(Path(VENV_PATH).parent)
#     return PROCESS_PATH

def get_batch_setup_location():
    # CORE_PYTHON_PATH = sys.base_prefix
    PROCESS_PATH = os.getcwd()
    return PROCESS_PATH

def create_batch(batch_script):
    src_run_bat = batch_script
    return src_run_bat

def save_script_to_file(file_path, content):
    if os.path.exists(file_path):
        print(f"File '{file_path}' already exists. Aborting save operation.")
    else:
        with open(file_path, 'w') as file:
            file.write(content)
        print(f"File '{file_path}' has been created and saved.")

def create_requirements_file(output_file="requirements.txt"):
    # Run pip freeze and capture the output
    result = subprocess.run(["pip", "freeze"], capture_output=True, text=True)
    # Write the output to requirements.txt
    with open(output_file, "w") as f:
        f.write(result.stdout)


if __name__ == '__main__':
    create_requirements_file()
    PROCESS_PATH = get_batch_setup_location()
    batch_script = batch_script.format( PROCESS_PATH=PROCESS_PATH )
    batch_script = create_batch(batch_script)
    file_name = "run.bat"
    file_path  = r"{PROCESS_PATH}\{file_name}".format(PROCESS_PATH=PROCESS_PATH,file_name=file_name)
    save_script_to_file(file_path,batch_script)
    
