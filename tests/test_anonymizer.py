import unittest

from services.anonymizer import anonymize_dialog_text


class AnonymizerTestCase(unittest.TestCase):
    def test_masks_common_personal_data(self):
        source = (
            "Ivan Petrov: телефон +7 (999) 123-45-67, карта 2200 0000 0000 0000, "
            "email ivan.petrov@example.com, паспорт 4500 123456\n"
            "Мария: СНИЛС 123-456-789 00, ИНН 7707083893, "
            "адрес: Москва, ул. Тверская, д. 1, кв. 2\n"
            "Ivan Petrov: мой ник @private_user\n"
        )

        result = anonymize_dialog_text(source)

        self.assertIn("[Участник 1]:", result)
        self.assertIn("[Участник 2]:", result)
        self.assertIn("[телефон]", result)
        self.assertIn("[номер карты]", result)
        self.assertIn("[email]", result)
        self.assertIn("[секретные данные]", result)
        self.assertIn("[адрес]", result)
        self.assertIn("[telegram_username]", result)
        self.assertNotIn("Ivan Petrov", result)
        self.assertNotIn("Мария", result)
        self.assertNotIn("999", result)
        self.assertNotIn("ivan.petrov@example.com", result)
        self.assertNotIn("Тверская", result)


if __name__ == "__main__":
    unittest.main()
