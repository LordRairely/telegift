import unittest

from services.feedback import parse_gift_ratings, strip_rating_fragments


class GiftAnalyticsTestCase(unittest.TestCase):
    def test_parse_gift_ratings(self):
        ratings = parse_gift_ratings("1: 5, 2: 3, 3: 4. Вторая слишком банальная")

        self.assertEqual([rating.gift_index for rating in ratings], [1, 2, 3])
        self.assertEqual([rating.rating for rating in ratings], [5, 3, 4])

    def test_strip_rating_fragments_keeps_comment(self):
        comment = strip_rating_fragments("1: 5, 2: 3. Вторая слишком банальная")

        self.assertIn("Вторая слишком банальная", comment)
        self.assertNotIn("1: 5", comment)


if __name__ == "__main__":
    unittest.main()
