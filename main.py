import time
import threading
import ctypes
import sys
import os
import subprocess
import platform
import shlex

from typing import Optional

from BlockingApps.blocker import Blocker
from BlockingApps.taskParser import Parser, Task

from calendar_url import ICAL_URL

RUNNING = True
CHECK_EVERY = 5 # Number of seconds that program will be asleep when checking the websites/apps
ICAL_URL = ICAL_URL.strip()


def _run_as_admin():
    """Restart the script with admin privileges if not already running as admin."""
    def run_as_admin_windows():
        if ctypes.windll.shell32.IsUserAnAdmin():
            return  # Already running as admin

        script = sys.executable  # Path to Python executable
        params = " ".join([f'"{arg}"' for arg in sys.argv])  # Preserve arguments

        # Relaunch script as Admin
        ctypes.windll.shell32.ShellExecuteW(None, "runas", script, params, None, 1)
        sys.exit()  # Exit the current process
    
    def run_as_admin_mac():
        if os.geteuid() == 0: # type: ignore
            return  # Already running as root

        script = shlex.quote(sys.executable)  # Path to Python executable
        params = " ".join([shlex.quote(arg) for arg in sys.argv])  # Preserve arguments

        # Use AppleScript to request admin rights
        applescript = f'do shell script "{script} {params}" with administrator privileges'
        subprocess.run(["osascript", "-e", applescript])
        sys.exit()  # Exit the current process

    system = platform.system().lower()
    if system == "windows":
        run_as_admin_windows()
    elif system == "darwin":
        run_as_admin_mac()

def _check_input_in_background():
    " Special thread that will be check to stop the loop"
    global RUNNING
    input("Press Enter to stop the program...\n")  # Wait for user input
    RUNNING = False  # Set the flag to False to break the loop
    print(f"Please wait {CHECK_EVERY} seconds for program to end")

def get_active_task(tasks: list[Task]) -> Optional[Task]:
    """Return the currently active task, if any."""
    for task in tasks:
        if task.is_active() and task.does_block_anything():
            return task
    return None

def unblock_all_tasks(tasks: list[Task], blocker: Blocker) -> None:
    " Make sure that all task are unlocked before exiting "
    for task in tasks:
        blocker.unblock_websites(
            task.blocking_info["block_websites"]
        )

def main() -> None:
    """
    Main process of the application that get the task by
    passed URL and starts the process of blocking websites
    and apps
    """
    _run_as_admin()
    parser = Parser()
    blocker = Blocker()
    tasks = parser.filter_task_by_today(parser.get_tasks(ICAL_URL))
    threading.Thread(target=_check_input_in_background).start()

    current_task = None
    try:
        while RUNNING:
            print("Running: ", RUNNING)
            active_task = get_active_task(tasks)

            if active_task and active_task != current_task:
                print(f"🔒 Blocking for task: {active_task.title}")
                if active_task.blocking_info:
                    blocker.block_apps(active_task.blocking_info["block_apps"])
                    blocker.block_websites(active_task.blocking_info["block_websites"])
                current_task = active_task

            elif current_task and not current_task.is_active():
                print(f"✅ Unblocking after task: {current_task.title}")
                blocker.unblock_websites(current_task.blocking_info["block_websites"])
                current_task = None

            elif current_task:
                blocker.block_apps(current_task.blocking_info["block_apps"])
            
            time.sleep(CHECK_EVERY)  # Check every 30 seconds

        # After ending the program's work make sure that all of the blockage was for sure ended!
        unblock_all_tasks(tasks, blocker)
    except Exception:
        # Even if something goes wrong make sure to unblock all tasks
        unblock_all_tasks(tasks, blocker)

if __name__ == '__main__':
    main()
