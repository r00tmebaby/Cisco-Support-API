import os
import unittest
from unittest.mock import mock_open, patch

from app.utils import (
    normalize_date_format,
    normalize_to_camel_case,
    save_to_json,
)


class TestUtilsFunctions(unittest.TestCase):

    @patch("os.makedirs")
    @patch("builtins.open", new_callable=mock_open)
    def test_save_to_json(self, mock_file, mock_makedirs):
        """Test saving data to a JSON file."""
        data = {"key": "value"}
        filename = "test.json"

        save_to_json(data, filename)

        mock_makedirs.assert_called_once_with(os.path.dirname(filename), exist_ok=True)

        # Join the content written to the file
        written_data = "".join(
            call_args[0][0] for call_args in mock_file().write.call_args_list
        )
        expected_data = '{\n    "key": "value"\n}'
        self.assertEqual(written_data, expected_data)

    def test_normalize_to_camel_case(self):
        """Test normalization of table header to camelCase."""
        header = "Some Header With Special Characters!"
        result = normalize_to_camel_case(header)
        self.assertEqual(result, "someHeaderWithSpecialCharacters")

    def test_normalize_date_format_valid(self):
        """Test normalization of a valid date string."""
        date_str = "01-Jan-2022"
        result = normalize_date_format(date_str, "%d-%b-%Y")
        self.assertEqual(result, "01-01-2022")

    def test_normalize_date_format_invalid(self):
        """Test handling of an invalid date string."""
        date_str = "invalid date"
        result = normalize_date_format(date_str, "%d-%b-%Y")
        self.assertEqual(result, "invalid date")


if __name__ == "__main__":
    unittest.main()
