# Realtime MRS Visualization

A Python application that visualizes E/I ratio in real-time using PsychoPy.

## Features

- Interactive menu-based task selection
- Visual feedback using a circle that changes size based on E/I ratio
- Configurable time limits for task execution
- Ability to return to the menu during a task
- Task introduction screens

## Setup

This project uses Poetry for dependency management. To set up:

1. Make sure you have Poetry installed: https://python-poetry.org/docs/#installation
2. Clone this repository
3. Run `poetry install` to install dependencies
4. Use `poetry shell` to activate the virtual environment

## Running the Application

Simply run the main script:

```
poetry run python run.py
```

This will launch the menu system where you can:
1. Select a task to run
2. Configure parameters like run time
3. Execute the task
4. Return to the menu when finished

## Task Information

### E/I Ratio Visualization

This task displays a circle that changes size based on the E/I ratio values received.
- The circle grows and shrinks as the ratio changes
- The current E/I ratio value is displayed on screen
- Press 'q' at any time to return to the menu
- If a time limit is set, a countdown timer is displayed

## Requirements

- Python 3.8-3.10
- Poetry

## Files

- `menu.py`: Task selection and configuration menu
- `ei_tcp_event_listener.py`: Creates a visualization window and listens for E/I values over TCP
- `sent_ei.py`: Simulates E/I values and sends them to the listener
- `run.py`: Main entry point for the application 