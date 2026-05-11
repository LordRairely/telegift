import unittest

from services.upload_limits import ADMIN_USERNAME, MAX_UPLOAD_ATTEMPTS, build_upload_limit_message, can_upload_more


class UploadLimitsTestCase(unittest.TestCase):
    def test_regular_user_can_upload_until_limit(self):
        self.assertEqual(MAX_UPLOAD_ATTEMPTS, 3)
        self.assertTrue(can_upload_more("regular_user", MAX_UPLOAD_ATTEMPTS - 1))
        self.assertFalse(can_upload_more("regular_user", MAX_UPLOAD_ATTEMPTS))

    def test_configured_admin_can_be_unlimited(self):
        self.assertTrue(can_upload_more(ADMIN_USERNAME, 100))

    def test_limit_message_points_to_configured_admin(self):
        message = build_upload_limit_message(MAX_UPLOAD_ATTEMPTS)

        self.assertIn(f"@{ADMIN_USERNAME}", message)


if __name__ == "__main__":
    unittest.main()
