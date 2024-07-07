# Mugsy: Operator Middleware
[![codecov](https://codecov.io/gh/margyle/operator/graph/badge.svg?token=Q1BR1UE0FG)](https://codecov.io/gh/margyle/operator)

Please note that this app is not ready for prime time just yet.  Please checkout the following blog posts for more info:
- Operator Overview: https://www.heymugsy.com/blog/2024/4/28/update-operator-middleware
- Current Status: [https://github.com/MugsyOS/Operator/issues/12](https://github.com/MugsyOS/Operator/issues/12)

## Introduction
This repository contains the source code for the Operator App, a FastAPI application designed to manage and control Mugsys hardware devices. All GPIO control is handled by Operator to keep hardware related functionality isolated from the primary DECAF api, allowing for increased hardware compatibility. 

Requests from the Mugsy frontend are sent to the DECAF API which handles all primary functionality. When a GPIO action is required, DECAF calls Operator to perform the action.

## Getting Started

### Prerequisites
Before you begin, ensure you have the following installed on your system:
- Python 3.8 or higher
- pip
- virtualenv (optional but recommended)

### Setting Up the Environment

To set up the project environment:
1. Clone the repository:
   ```bash
   git clone https://github.com/margyle/operator.git
   cd operator
   ```

2. Create and activate a virtual environment (optional but recommended):
   - For Unix/MacOs:
     ```bash
     python -m venv venv
     source venv/bin/activate
     ```
   - For Windows:
     ```cmd
     python -m venv venv
     venv\Scripts\activate
     ```


### Installing the Application

#### Development Mode
To install the application in editable mode, which is recommended for development purposes:
```bash
pip install -e .
```
This command allows you to modify the source code and see changes without reinstalling the package.

#### Production Mode
To install the application for production use:
```bash
pip install .
```
This command installs the application as a standard Python package.

## Usage

To start the FastAPI application, run:
```bash
uvicorn operator_app.app:app --reload --host 0.0.0.0 --port 8000
```
This command will start the FastAPI server with live reloading enabled.

## Tests

To run tests, run:
```bash
pytest
```

## Troubleshooting

If you are getting import errors, you may need to add your app source to the ENV, run:
```bash
export PYTHONPATH=$PYTHONPATH:/path/to/Operator/src
```

## Contributing
Contributions to this project are welcome. Please ensure that all pull requests are well-documented and include tests where applicable.

## Third-Party Libraries

### Modified Library File

The file `src/operator_services/libs/hx711.py` in this project was based on [HX711](https://github.com/gandalf15/HX711) which is licensed under the BSD 3-Clause License, Copyright (c) 2017, Marcel Zak. Modifications were made to make it compatible with pigpio.

Original Library License: [BSD 3-Clause License](https://opensource.org/licenses/BSD-3-Clause)

Please refer to the original source for the unmodified version and further details about the library.

