from django.test import TestCase

from .sap_pyrfc import _aviso_esta_cerrado


class SapAvisoStatusTests(TestCase):
    def test_mece_closes_notification(self):
        self.assertTrue(_aviso_esta_cerrado({'MECE', 'ORAS'}))

    def test_meab_closes_notification(self):
        self.assertTrue(_aviso_esta_cerrado({'MEAB'}))

    def test_oras_alone_does_not_close_notification(self):
        self.assertFalse(_aviso_esta_cerrado({'ORAS'}))
