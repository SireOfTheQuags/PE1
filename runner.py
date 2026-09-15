import subprocess
import os

# Get the directory where this python script lives
current_dir = os.path.dirname(os.path.abspath(__file__))
bat_file = os.path.join(current_dir, "push.bat")

# This opens a real, independent command prompt window that allows user input
subprocess.run(f'start cmd /k "{bat_file}"', shell=True)