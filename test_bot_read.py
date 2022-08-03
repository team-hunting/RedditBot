
import unittest
from unittest.mock import MagicMock, patch
from bot_read import Bot

class BotRunTestCase(unittest.TestCase):
    @patch('bot_read.Bot.__new__')
    def test_BotRun(self, fake_new):
        mock_inst = MagicMock()
        mock_inst.run.return_value = "Fake Run!"
        fake_new.return_value = mock_inst

        bot = Bot()
        e = bot.run()
        self.assertEqual(e, "Fake Run!")

if __name__ == '__main__':
    unittest.main()