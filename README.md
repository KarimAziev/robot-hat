# Robot Hat

[![codecov](https://codecov.io/gh/KarimAziev/robot-hat/graph/badge.svg?token=2C863KHRLU)](https://codecov.io/gh/KarimAziev/robot-hat)

`robot_hat` is a custom Python library designed for the Raspberry Pi. It builds on and improves the original [Sunfounder Robot Hat Python library](https://github.com/sunfounder/robot-hat/tree/v2.0) by introducing significant enhancements, fixes, and improvements.

> **Note:** While not all modules are fully compatible with the original library, most of them are supported and can be used in similar ways.

<!-- markdown-toc start - Don't edit this section. Run M-x markdown-toc-refresh-toc -->

**Table of Contents**

> - [Robot Hat](#robot-hat)
>   - [Installation](#installation)
>   - [Key Features](#key-features)
>     - [No sudo](#no-sudo)
>     - [Type Hints](#type-hints)
>     - [Bug Fixes](#bug-fixes)
>     - [Mock Support for Testing](#mock-support-for-testing)
>   - [Development Environment Setup](#development-environment-setup)
>     - [Prerequisites](#prerequisites)
>     - [Steps to Set Up](#steps-to-set-up)
>   - [Distribution](#distribution)
>   - [Common Commands](#common-commands)
>   - [Notes & Recommendations](#notes--recommendations)

<!-- markdown-toc end -->

## Installation

Install this via pip (or your favourite package manager):

```bash
pip install robot-hat
```

## Key Features

### No sudo

The original library includes several instances of unnecessary `sudo` usage. For example:

```python
User = os.popen('echo ${SUDO_USER:-$LOGNAME}').readline().strip()
UserHome = os.popen('getent passwd %s | cut -d: -f 6' % User).readline().strip()
config_file = '%s/.config/robot-hat/robot-hat.conf' % UserHome
```

This approach elevates permissions unnecessarily, even for reading the login name. All such patterns have been removed in this library.

### Type Hints

This version prioritizes:

- **Type hints** for better developer experience.
- Modular, maintainable, and well-documented code.

### Bug Fixes

Numerous bugs from the original implementation have been identified and resolved.

### Mock Support for Testing

Development and testing are now possible on non-Raspberry Pi platforms, thanks to the support of mocks. To enable mocking, set the following environment variables before importing the `robot_hat` library:

```python
import os
os.environ["GPIOZERO_PIN_FACTORY"] = "mock"
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
```

---

## Development Environment Setup

### Prerequisites

1. **Python 3.10 or newer** must be installed.
2. Ensure you have `pip` installed (a recent version is recommended):
   ```bash
   python3 -m pip install --upgrade pip
   ```

### Steps to Set Up

1. **Clone the Repository**:

   ```bash
   git clone https://github.com/KarimAziev/robot-hat.git
   cd robot-hat
   ```

2. **Set Up a Virtual Environment**:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # Linux/Mac
   # OR
   .venv\Scripts\activate     # Windows
   ```

3. **Upgrade Core Tools**:

   ```bash
   pip install --upgrade pip setuptools wheel
   ```

4. **Install in Development Mode**:
   ```bash
   pip install -e ".[dev]"  # Installs all dev dependencies (e.g., black, isort, pre-commit)
   ```

---

## Distribution

To create distributable artifacts (e.g., `.tar.gz` and `.whl` files):

1. Install the build tool:

   ```bash
   pip install build
   ```

2. Build the project:
   ```bash
   python -m build
   ```
   The built files will be located in the `dist/` directory:

- Source distribution: `robot_hat-x.y.z.tar.gz`
- Wheel: `robot_hat-x.y.z-py3-none-any.whl`

These can be installed locally for testing or uploaded to PyPI for distribution.

---

## Common Commands

- **Clean Build Artifacts**:
  ```bash
  rm -rf build dist *.egg-info
  ```
- **Deactivate Virtual Environment**:
  ```bash
  deactivate
  ```

---

## Notes & Recommendations

- The library uses `setuptools_scm` for versioning, which dynamically determines the version based on Git tags. Use proper semantic versioning (e.g., `v1.0.0`) in your repository for best results.
- Development tools like `black` (code formatter) and `isort` (import sorter) are automatically installed with `[dev]` dependencies.
