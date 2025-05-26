#!/usr/bin/env python3
"""
Main entry point for the realtime-mrs application.
Launches the menu system in a new Terminal window (macOS only).
"""
import platform
import subprocess
import sys
import os

def main():
    if platform.system() == "Darwin":
        # macOS: open a new Terminal window and run the menu
        project_dir = os.path.abspath(os.path.dirname(__file__))
        menu_cmd = f'cd {project_dir}; poetry run python menu.py'
        # Escape double quotes for AppleScript
        menu_cmd_escaped = menu_cmd.replace('"', '\\"')
        osa_cmd = [
            "osascript", "-e",
            f'tell application "Terminal" to do script "{menu_cmd_escaped}"'
        ]
        print("Opening the menu in a new Terminal window...")
        subprocess.Popen(osa_cmd)
        print("You can close this window or use it for other tasks.")
    else:
        # Fallback: just run the menu in the current terminal
        from menu import TaskMenu
        menu = TaskMenu()
        menu.run()

if __name__ == "__main__":
    main() 