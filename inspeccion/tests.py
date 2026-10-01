from django.test import TestCase

from .sap_pyrfc import _aviso_esta_cerrado


class SapAvisoStatusTests(TestCase):
    def test_i0072_closes_notification(self):
        self.assertTrue(_aviso_esta_cerrado({'I0072', 'I0068'}))

    def test_other_active_statuses_do_not_close_notification(self):
        self.assertFalse(_aviso_esta_cerrado({'I0068', 'I0069'}))
