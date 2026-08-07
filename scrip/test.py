import subprocess

def create_requirements_file(output_file="xxx_requirements.txt"):
    # Run pip freeze and capture the output
    result = subprocess.run(["pip", "freeze"], capture_output=True, text=True)
    # Write the output to requirements.txt
    with open(output_file, "w") as f:
        f.write(result.stdout)

if __name__ == "__main__":
    create_requirements_file()
    print("requirements.txt has been created!")
