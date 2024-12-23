import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, List, Optional, TypeVar, Union

from robot_hat.exceptions import FileDBValidationError

logger = logging.getLogger(__name__)

T = TypeVar("T")


@dataclass
class FileDB(object):
    """
    A lightweight file-based key-value database.

    This class provides an easy way to store, retrieve, and manage key-value
    pairs in a simple text file. It's convenient for handling configuration
    files and calibration values for robots or similar applications.

    Example file format:
        # robot-hat configuration file
        speed = 100
        calibration = 1.23
    """

    db: str

    def __post_init__(self):
        """
        Ensures that the database file exists when the class is initialized.

        If the file doesn't exist, it will be created, along with necessary
        parent directories. A default comment header will also be written.
        """
        if not self.db:
            raise ValueError("db: Missing file path parameter.")
        FileDB.file_check_create(self.db)

    @staticmethod
    def file_check_create(
        file: str,
    ) -> None:
        """
        Ensures the specified file exists.

        If the file doesn't exist, it creates the file and its parent directories
        as needed. Adds a simple header to newly created files. If something
        already exists with the same name but it's a directory, raises an error.
        """
        logger.debug("Checking file %s", file)
        file_path = Path(file)
        if file_path.exists():
            if file_path.is_dir():
                raise IsADirectoryError(
                    f"Could not create file %s, there is a folder with the same name",
                    file,
                )
        else:
            try:
                file_path.parent.mkdir(exist_ok=True, parents=True)
                file_path.write_text(
                    "# robot-hat config and calibration value of robots\n\n"
                )
            except Exception as e:
                logger.error("Error creating file", exc_info=True)
                raise e

    def get(self, name: str, default_value: T) -> Union[T, str]:
        """
        Retrieves the value for a given key from the database file.

        If the key is missing, returns the provided default value instead.
        Skips malformed lines (those without an "=").

        Example:
            speed = db.get("speed", 50)  # Returns 50 if "speed" isn't present.
        """
        for line in self.parse_file():
            if "=" not in line:
                logger.warning("Skipping malformed line: '%s'", line)
                continue
            key, _, val = line.partition("=")
            if key.strip() == name:
                return val.replace(" ", "").strip()
        return default_value

    def get_value_with(self, name: str, fn: Callable[[str], T]) -> Optional[T]:
        """
        Retrieves a single value associated with a given key in the database and
        processes it using a provided conversion function.

        This method looks up the specified key in the database, retrieves its
        value as a string, and applies the provided conversion function (`fn`)
        to transform the value into the desired type. If the key is missing or
        the value is `None`, `None` is returned.

        Args:
            name: The key to look up in the database.
            fn: A function that converts a string value into the desired type
            (e.g., `int`, `float`, or a custom type).

        Returns:
            The transformed value after applying the provided function, or `None` if the value is missing or `None`.

        Example:
            Assuming the database contains the key-value pair `"key" = "123"`:
                result = get_value_with("key", int)  # result is 123

            For the key-value pair `"key" = "45.67"`:
                result = get_value_with("key", float)  # result is 45.67

            If `"key"` is missing or set to an empty value:
                result = get_value_with("key", int)  # result is None
        """
        value = self.get(name, default_value=None)
        if value:
            return fn(value)

    @staticmethod
    def split_list_str(value: str) -> List[str]:
        """
        Splits a string representation of a list into individual string elements.

        The input string is expected to be a comma-separated list of elements
        enclosed in square brackets (e.g., "[a, b, c]"). Leading and trailing
        whitespace around elements is removed. Empty elements are ignored.

        Args:
            value (str): The string representation of a list to parse.

        Returns:
            List[str]: A list of strings extracted from the input string.

        Example:
            input = "[ a, 1.3 , c ]"
            output = ["a", "1.3", "c"]

            input = "[]"
            output = []
        """
        return [i.strip() for i in value.strip("[]").split(",") if i.strip()]

    def get_list_value_with(self, name: str, fn: Callable[[str], T]) -> List[T]:
        """
        Retrieves a list value associated with a given key in the database and processes
        each element using a provided conversion function.

        This method retrieves the value for the specified key, parses it into a list
        of strings, and applies the provided conversion function (`fn`) to each element
        in the list. The converted list is returned.

        Args:
            name (str): The key to look up in the database.
            fn: A function that maps a string element to the desired type
                (e.g., `int` for integers, `float` for floating-point numbers).

        Returns:
            A list of elements converted using the provided function `fn`.

        Example:
            Assuming the database contains the key-value pair `"key" = "[1, 2, 3]"`:
                result = get_list_value_with("key", int)  # result is [1, 2, 3]

            For the input with `"key" = "[1.1, 2.2, 3.3]"`:
                result = get_list_value_with("key", float)  # result is [1.1, 2.2, 3.3]
        """
        elems = self.split_list_str(self.get(name, default_value="[]"))

        return [fn(v) for v in elems]

    def read_int_list(self, name: str, default_value: List[int] = []) -> List[int]:
        """
        Reads and returns a list of integers from the database for the given key.

        The value associated with the key is expected to be a comma-separated list
        of integers enclosed in square brackets (e.g., "[1,2,3]"). If the key is
        missing or the value cannot be parsed, the provided default value is returned.

        Args:
            name: The key to look up in the database.
            default_value: The default list of integers to return if the key is missing or invalid.

        Returns:
            A list of integers parsed from the database value, or the default value if parsing fails.
        """
        value = self.get_list_value_with(name, int)
        return value or default_value

    def read_float_list(
        self, name: str, default_value: List[float] = []
    ) -> List[float]:
        """
        Reads and returns a list of floating-point numbers from the database for the given key.

        The value associated with the key is expected to be a comma-separated list
        of floating-point numbers enclosed in square brackets (e.g., "[1.1,2.2,3.3]").
        If the key is missing or the value cannot be parsed, the provided default value is returned.

        Args:
            name: The key to look up in the database.
            default_value: The default list of floats to return
                if the key is missing or invalid. Defaults to an empty list ([]).

        Returns:
            A list of floating-point numbers parsed from the database value,
            or the default value if parsing fails.
        """
        return self.get_list_value_with(name, float) or default_value

    def parse_file(self) -> List[str]:
        """
        Reads and parses the database file, ignoring comments and blank lines.

        Returns a list of lines with the format "key = value". Lines that are
        empty or begin with "#" are excluded.
        """
        try:
            with open(self.db, "r") as conf:
                return [
                    line.strip() for line in conf if line.strip() and line[0] != "#"
                ]
        except FileNotFoundError:
            with open(self.db, "w") as conf:
                conf.write("")
            return []

    def set(self, name: str, value: str) -> None:
        """
        Sets or updates a key-value pair in the database file.

        If the key already exists, its value will be updated; otherwise, the
        key-value pair will be appended to the end of the file. If the file
        write operation fails, the original file remains unchanged because of
        the atomic file-writing mechanism.

        Raises a ValueError if the key is empty, contains "=", or the value
        contains newline characters.
        """
        if not name or "=" in name:
            raise FileDBValidationError(
                f"Invalid name: '{name}' cannot be empty or contain '='"
            )
        if "\n" in value:
            raise FileDBValidationError("Value cannot contain newline characters")

        lines = []

        with open(self.db, "r") as conf:
            lines = conf.readlines()

        found = False

        for i, line in enumerate(lines):
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            parts = [item.strip() for item in line.split("=") if item.strip()]

            if parts and len(parts) > 0 and parts[0] == name:
                lines[i] = f"{name} = {value}\n"
                found = True

        if not found:
            lines.append(f"{name} = {value}\n")

        with open(f"{self.db}.tmp", "w") as tmp:
            tmp.writelines(lines)

        os.rename(f"{self.db}.tmp", self.db)

    def get_all_as_dict(self) -> Dict[str, str]:
        """
        Returns all key-value pairs from the database file as a dictionary.

        Keys and values are stripped of extraneous whitespace. Malformed lines
        are skipped, and comments are ignored.

        Example:
            config = db.get_all_as_dict()
            print(config)  # {'speed': '100', 'calibration': '1.23'}
        """
        data = {}
        for line in self.parse_file():
            key, _, val = line.partition("=")
            data[key.strip()] = val.replace(" ", "").strip()
        return data
