# Robot Hat

This is a rewritten version of [Sunfounder's Robot Hat Python library](https://github.com/sunfounder/robot-hat/tree/v2.0) for Raspberry Pi.

## Installation

You can install the `robot_hat` library in multiple ways, depending on your needs.

### Install the Latest Version Directly from GitHub

If you want to get the latest development version of the library (from the **`main` branch**) directly from GitHub, use:

```bash
pip install git+https://github.com/KarimAziev/robot_hat.git@main#egg=robot_hat
```

#### Example: `requirements.txt`

Add this line to your `requirements.txt` to always install the latest version:

```plaintext
git+https://github.com/KarimAziev/robot_hat.git@main#egg=robot_hat
```

---

### Install a Specific Tag (Versioned Release)

If you want to install a specific release version of the library (e.g., `v1.0.1`), you can reference that tag from GitHub:

```bash
pip install git+https://github.com/KarimAziev/robot_hat.git@v1.0.1#egg=robot_hat
```

#### Example: `requirements.txt`

To lock the installation to a specific version (e.g., `v1.0.1`):

```plaintext
git+https://github.com/KarimAziev/robot_hat.git@v1.0.1#egg=robot_hat
```

---

### Install from a Specific Commit

To install the library at a particular commit, replace `<commit_hash>` with the desired commit hash:

```bash
pip install git+https://github.com/KarimAziev/robot_hat.git@<commit_hash>#egg=robot_hat
```

#### Example: `requirements.txt`

If you know the exact Git commit hash to reference:

```plaintext
git+https://github.com/KarimAziev/robot_hat.git@a1b2c3d4#egg=robot_hat
```

---

### Include Development Dependencies

If your library has optional development dependencies (e.g., for linting, testing, or contributing), you can install them using the `[dev]` extras marker, like so:

```bash
pip install "robot_hat[dev]"
```

Or, to install from GitHub with `dev` dependencies:

```bash
pip install git+https://github.com/KarimAziev/robot_hat.git@main#egg=robot_hat[dev]
```

#### Example: `requirements.txt`

```plaintext
git+https://github.com/KarimAziev/robot_hat.git@main#egg=robot_hat[dev]
```

---

### Verifying the Installation

After installing the library, you can verify it is installed and working properly:

```bash
python -c "import robot_hat; print(robot_hat.__version__)"
```

This will print the version of the library installed. If you are using `setuptools_scm`, the version will reflect your Git tags or branch state.

---

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
