import os
import unittest

from robot_hat.exceptions import FileDBValidationError
from robot_hat.filedb import FileDB


class TestFileDB(unittest.TestCase):
    def setUp(self):
        """
        Create a temporary database file for testing.
        """
        self.test_db_path = "test_database.txt"
        self.db = FileDB(self.test_db_path)

    def tearDown(self):
        """
        Clean up the temporary database file after tests are done.
        """
        try:
            os.remove(self.test_db_path)
        except FileNotFoundError:
            pass

    def test_file_creation_on_init(self):
        """
        Test that the database file is created on initialization
        if it does not already exist.
        """
        if os.path.exists(self.test_db_path):
            os.remove(self.test_db_path)
        self.db = FileDB(self.test_db_path)
        self.assertTrue(os.path.exists(self.test_db_path))

    def test_file_check_create(self):
        """
        Test that a file is created correctly and no error is raised
        when the path already exists.
        """
        FileDB.file_check_create(self.test_db_path)
        self.assertTrue(os.path.exists(self.test_db_path))

    def test_file_check_create_directory_error(self):
        """
        Test that attempting to create a database file with a directory
        of the same name raises IsADirectoryError.
        """
        if os.path.exists(self.test_db_path):
            os.remove(self.test_db_path)
        os.mkdir(self.test_db_path)
        with self.assertRaises(IsADirectoryError):
            FileDB.file_check_create(self.test_db_path)
        os.rmdir(self.test_db_path)

    def test_set_and_get(self):
        """
        Test setting and retrieving a value from the database file.
        """
        self.db.set("key", "value")
        retrieved_value = self.db.get("key", default_value="default")
        self.assertEqual(retrieved_value, "value")

    def test_get_default_value(self):
        """
        Test that the default value is returned for a missing key.
        """
        retrieved_value = self.db.get("missing_key", default_value="default_value")
        self.assertEqual(retrieved_value, "default_value")

    def test_set_invalid_key(self):
        """
        Test that setting a key with an invalid format raises a ValueError.
        """
        with self.assertRaises(FileDBValidationError):
            self.db.set("invalid=key", "value")

    def test_set_invalid_value(self):
        """
        Test that setting a value containing a newline raises a ValueError.
        """
        with self.assertRaises(FileDBValidationError):
            self.db.set("key", "invalid\nvalue")

    def test_parse_file(self):
        """
        Test parsing of valid and invalid lines in the file.
        """
        with open(self.test_db_path, "w") as f:
            f.write("# This is a comment\n")
            f.write("key = value\n")
            f.write("# invalid_line\n")
        parsed_lines = self.db.parse_file()
        self.assertEqual(len(parsed_lines), 1)
        self.assertEqual(parsed_lines[0], "key = value")

    def test_get_all_as_dict(self):
        """
        Test reading all key-value pairs as a dictionary.
        """
        self.db.set("key1", "value1")
        self.db.set("key2", "value2")
        all_data = self.db.get_all_as_dict()
        self.assertEqual(len(all_data), 2)
        self.assertEqual(all_data["key1"], "value1")
        self.assertEqual(all_data["key2"], "value2")

    def test_get_value_with(self):
        """
        Test transforming a saved string value into a desired type.
        """
        self.db.set("number", "123")
        retrieved_value = self.db.get_value_with("number", int)
        self.assertEqual(retrieved_value, 123)

    def test_get_list_value_with(self):
        """
        Test retrieving a list and transforming its elements using a function.
        """
        self.db.set("numbers", "[1, 2, 3]")
        retrieved_list = self.db.get_list_value_with("numbers", int)
        self.assertEqual(retrieved_list, [1, 2, 3])

    def test_read_int_list(self):
        """
        Test reading a list of integers.
        """
        self.db.set("int_list", "[1, 2, 3]")
        retrieved_list = self.db.read_int_list("int_list")
        self.assertEqual(retrieved_list, [1, 2, 3])

    def test_read_float_list(self):
        """
        Test reading a list of floating-point numbers.
        """
        self.db.set("float_list", "[1.1, 2.2, 3.3]")
        retrieved_list = self.db.read_float_list("float_list")
        self.assertEqual(retrieved_list, [1.1, 2.2, 3.3])

    def test_split_list_str(self):
        """
        Test splitting a string into a list of strings.
        """
        test_string = "[a, b, c]"
        expected_output = ["a", "b", "c"]
        self.assertEqual(FileDB.split_list_str(test_string), expected_output)

    def test_missing_file_parse(self):
        """
        Test that parsing a non-existent file creates it and returns an empty list.
        """
        os.remove(self.test_db_path)
        parsed_lines = self.db.parse_file()
        self.assertEqual(parsed_lines, [])
        self.assertTrue(os.path.exists(self.test_db_path))


if __name__ == "__main__":
    unittest.main()
