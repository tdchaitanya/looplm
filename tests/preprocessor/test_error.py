"""Tests for FileProcessingError."""

import pytest

from looplm.preprocessor.files import FileProcessingError


class TestFileProcessingError:
    """Tests for the FileProcessingError class."""

    def test_init(self):
        """Test initialization of FileProcessingError."""
        error = FileProcessingError("Test error message", "test_file.txt")

        assert error.message == "Test error message"
        assert error.file_path == "test_file.txt"
        assert str(error) == "Error processing file 'test_file.txt': Test error message"

    def test_raise_and_catch(self):
        """Test raising and catching FileProcessingError."""

        def raise_error():
            raise FileProcessingError("Cannot process file", "example.txt")

        with pytest.raises(FileProcessingError) as excinfo:
            raise_error()

        assert "Cannot process file" in str(excinfo.value)
        assert "example.txt" in str(excinfo.value)
        assert excinfo.value.file_path == "example.txt"
        assert excinfo.value.message == "Cannot process file"
