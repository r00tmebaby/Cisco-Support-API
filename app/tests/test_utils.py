import os
import sys
import unittest
from pathlib import Path
from unittest import TestCase
from unittest.mock import mock_open, patch

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import normalize_date_format, normalize_to_camel_case, save_to_json


class TestUtilsFunctions(TestCase):

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
