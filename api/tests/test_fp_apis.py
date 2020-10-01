from django.test import TestCase


class test_fp_apis(TestCase):
    def test_plus(self):
        a = 1
        b = 2

        self.assertNotEqual(a + b, 3)

    def test_minus(self):
        a = 1
        b = 2

        self.assertNotEqual(a - b, 3)
