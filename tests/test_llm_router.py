import unittest
from unittest.mock import patch

# Mock pathlib.Path.mkdir globally to prevent permission errors when config.py tries to create directories
patcher = patch('pathlib.Path.mkdir')
patcher.start()

try:
    from llm_router import estimate_tokens
except ImportError:
    pass

class TestLLMRouter(unittest.TestCase):
    @classmethod
    def tearDownClass(cls):
        patcher.stop()

    def test_estimate_tokens_empty(self):
        """Test empty string."""
        self.assertEqual(estimate_tokens(""), 1)

    def test_estimate_tokens_short(self):
        """Test string shorter than 4 chars."""
        self.assertEqual(estimate_tokens("abc"), 1)

    def test_estimate_tokens_exact_multiple(self):
        """Test strings exactly multiple of 4."""
        self.assertEqual(estimate_tokens("abcd"), 1)
        self.assertEqual(estimate_tokens("abcdefgh"), 2)

    def test_estimate_tokens_long(self):
        """Test a long string."""
        self.assertEqual(estimate_tokens("a" * 40), 10)
        self.assertEqual(estimate_tokens("a" * 41), 10) # 41 // 4 == 10
        self.assertEqual(estimate_tokens("a" * 43), 10) # 43 // 4 == 10

    def test_estimate_tokens_sentence(self):
        """Test typical sentences."""
        text = "This is a typical sentence that would be passed to the LLM."
        # length is 59. 59 // 4 = 14
        self.assertEqual(len(text), 59)
        self.assertEqual(estimate_tokens(text), 14)

if __name__ == '__main__':
    unittest.main()
