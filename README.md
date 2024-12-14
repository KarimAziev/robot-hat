# Robot Hat

This is a rewritten version of [Sunfounder's Robot Hat Python library](https://github.com/sunfounder/robot-hat/tree/v2.0) for Raspberry Pi.

## Setting Up Development Environment

To set up a fresh development environment for the `robot_hat` project, follow these steps:

### Prerequisites

1. Ensure you have Python 3.10 or newer installed.
2. Install `pip` (comes bundled with Python) and upgrade it to the latest version:
   ```bash
   python3 -m pip install --upgrade pip
   ```

### Steps to Set Up the Environment

1. Clone the repository:

   ```bash
   git clone https://github.com/KarimAziev/robot_hat.git
   cd robot_hat
   ```

2. Create and activate a virtual environment:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # For Linux/Mac
   # or
   .venv\Scripts\activate     # On Windows
   ```

3. Upgrade core tools inside the virtual environment:

   ```bash
   pip install --upgrade pip setuptools wheel
   ```

4. Install the project in editable (development) mode with all dependencies:
   ```bash
   pip install -e ".[dev]"  # Includes dev dependencies like black, pre-commit, isort
   ```

---

### Building the Project

To build the project for distribution, e.g., creating `.tar.gz` and `.whl` files:

1. Install the build tool:

   ```bash
   pip install build
   ```

2. Build the distribution:
   ```bash
   python -m build
   ```

This will generate a `dist/` directory containing the following artifacts:

- Source distribution (`robot_hat-x.y.z.tar.gz`)
- Wheel file (`robot_hat-x.y.z-py3-none-any.whl`)

You can install these locally for testing or upload them to PyPI for publishing.

---

## Common Commands

- **Clean build artifacts:**
  ```bash
  rm -rf build dist *.egg-info
  ```
- **Deactivate virtual environment:**
  ```bash
  deactivate
  ```

---

## Notes

- This project uses `setuptools_scm` to handle versioning, based on the Git tags of the repository. Ensure you use proper semver tags like `v1.0.0` to manage versions correctly.
- Dev dependencies (like `black`, `isort`) are automatically installed when running `pip install -e ".[dev]"`.
