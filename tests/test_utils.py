import unittest
from unittest.mock import patch, mock_open
import os
from utils import save_to_json, normalize_to_camel_case, normalize_date_format


class TestUtilsFunctions(unittest.TestCase):

    @patch("os.makedirs")
    @patch("builtins.open", new_callable=mock_open)
    def test_save_to_json(self, mock_file, mock_makedirs):
        """Test saving data to a JSON file."""
        data = {"key": "value"}
        filename = "test.json"

        save_to_json(data, filename)

        mock_makedirs.assert_called_once_with(os.path.dirname(filename), exist_ok=True)
        mock_file().write.assert_called_once()
        mock_file().write.assert_any_call('{\n    "key": "value"\n}')

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


if __name__ == '__main__':
    unittest.main()
