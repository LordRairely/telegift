import tempfile
import unittest
from pathlib import Path

from services.parser import parse_dialog_file, parse_telegram_json
from services.prompts import build_dialog_question_prompt, build_gift_prompt
from services.referrals import parse_start_source


class ParserTestCase(unittest.TestCase):
    def test_parse_txt_file(self):
        with tempfile.NamedTemporaryFile("w", suffix=".txt", encoding="utf-8", delete=False) as f:
            f.write("Alice: мой телефон +7 999 123 45 67\n")
            file_path = f.name

        try:
            result = parse_dialog_file(file_path)
        finally:
            Path(file_path).unlink()

        self.assertIn("[телефон]", result)
        self.assertNotIn("+7 999 123 45 67", result)

    def test_parse_txt_file_uses_file_sender_as_gift_giver(self):
        sender_user = {
            "id": 1,
            "first_name": "Alice",
            "last_name": "Example",
            "username": "alice",
        }

        with tempfile.NamedTemporaryFile("w", suffix=".txt", encoding="utf-8", delete=False) as f:
            f.write(
                "Alice Example: Я хочу выбрать подарок для Bob Example\n"
                "Bob Example: Мне нравятся кофе и настольные игры\n"
            )
            file_path = f.name

        try:
            result = parse_dialog_file(file_path, sender_user=sender_user)
        finally:
            Path(file_path).unlink()

        self.assertIn("Подаркодаритель:", result)
        self.assertIn("Подаркополучатель:", result)
        self.assertIn("Подаркополучатель: Мне нравятся кофе", result)
        self.assertNotIn("Alice", result)
        self.assertNotIn("Bob", result)

    def test_rejects_unknown_extension(self):
        with self.assertRaises(ValueError):
            parse_dialog_file("chat.csv")

    def test_parse_telegram_json_uses_gift_roles_and_masks_names(self):
        source = """
{
  "personal_information": {
    "user_id": 1,
    "first_name": "Alice",
    "last_name": "Example"
  },
  "messages": [
    {
      "type": "message",
      "from": "Alice Example",
      "from_id": "user1",
      "text": "Я хочу выбрать подарок для Bob Example"
    },
    {
      "type": "message",
      "from": "Bob Example",
      "from_id": "user2",
      "text": "Bob Example любит кофе и настольные игры"
    }
  ]
}
"""
        with tempfile.NamedTemporaryFile("w", suffix=".json", encoding="utf-8", delete=False) as f:
            f.write(source)
            file_path = f.name

        try:
            result = parse_telegram_json(file_path)
        finally:
            Path(file_path).unlink()

        self.assertIn("Подаркодаритель:", result)
        self.assertIn("Подаркополучатель:", result)
        self.assertIn("Подаркополучатель любит кофе", result)
        self.assertNotIn("Alice Example", result)
        self.assertNotIn("Bob Example", result)

    def test_parse_telegram_json_uses_file_sender_as_gift_giver(self):
        source = """
{
  "personal_information": {
    "user_id": 2,
    "first_name": "Bob",
    "last_name": "Example"
  },
  "messages": [
    {
      "type": "message",
      "from": "Alice Example",
      "from_id": "user1",
      "text": "Я думаю, что Bob Example понравятся книги"
    },
    {
      "type": "message",
      "from": "Bob Example",
      "from_id": "user2",
      "text": "Мне нравятся кофе и настольные игры"
    }
  ]
}
"""
        sender_user = {
            "id": 1,
            "first_name": "Alice",
            "last_name": "Example",
            "username": "alice",
        }

        with tempfile.NamedTemporaryFile("w", suffix=".json", encoding="utf-8", delete=False) as f:
            f.write(source)
            file_path = f.name

        try:
            result = parse_telegram_json(file_path, sender_user=sender_user)
        finally:
            Path(file_path).unlink()

        self.assertIn("Подаркодаритель:", result)
        self.assertIn("Подаркополучатель:", result)
        self.assertIn("Подаркополучатель понравятся книги", result)
        self.assertIn("Подаркополучатель: Мне нравятся кофе", result)
        self.assertNotIn("Alice", result)
        self.assertNotIn("Bob", result)

    def test_prompt_targets_gift_recipient(self):
        prompt = build_gift_prompt("Подаркодаритель: привет")

        self.assertIn("именно для Подаркополучателя", prompt)
        self.assertIn("Не предлагай подарки для Подаркодарителя", prompt)
        self.assertIn("какие 1-2 сигнала из диалога", prompt)
        self.assertIn("вариант до 2000 рублей", prompt)
        self.assertIn("Сценарии подарка", prompt)
        self.assertIn("Топ-1 выбор", prompt)

    def test_prompt_includes_gift_context(self):
        prompt = build_gift_prompt(
            "Подаркополучатель: люблю кофе",
            gift_context="Повод: день рождения\nБюджет: до 5000",
        )

        self.assertIn("Контекст от Подаркодарителя", prompt)
        self.assertIn("Повод: день рождения", prompt)
        self.assertIn("Бюджет: до 5000", prompt)

    def test_dialog_question_prompt_requires_evidence(self):
        prompt = build_dialog_question_prompt(
            "Подаркополучатель: люблю зелёный цвет",
            "Какой любимый цвет?",
        )

        self.assertIn("строго по анонимизированной переписке", prompt)
        self.assertIn("В переписке нет ответа на этот вопрос", prompt)
        self.assertIn("фразы-сигнала", prompt)

    def test_parse_start_source(self):
        self.assertEqual(parse_start_source("/start"), ("organic", None))
        self.assertEqual(parse_start_source("/start tg_123"), ("referral", "tg_123"))
        self.assertEqual(parse_start_source("/start ads_may"), ("ads_may", None))


if __name__ == "__main__":
    unittest.main()
