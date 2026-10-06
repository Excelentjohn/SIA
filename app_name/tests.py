from datetime import date

from django.test import TestCase
from django.urls import reverse

from .models import LostFound


class DashboardViewTests(TestCase):
    def setUp(self):
        LostFound.objects.create(
            item_name='Black Backpack',
            description='A black backpack left in the library study room.',
            category='BAGS',
            location='Library',
            date=date(2026, 10, 4),
            status='FOUND',
            owner_name='John Doe',
        )
        LostFound.objects.create(
            item_name='Silver Key',
            description='A silver key recovered from the science labs.',
            category='KEYS',
            location='Science Hall',
            date=date(2026, 10, 5),
            status='LOST',
            owner_name='Jane Doe',
        )

    def test_dashboard_renders_archive_summary_and_records(self):
        response = self.client.get(reverse('dashboard'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'THE LOST OBJECT ARCHIVE')
        self.assertContains(response, 'Black Backpack')
        self.assertContains(response, 'Silver Key')
        self.assertContains(response, 'FOUND')
        self.assertContains(response, 'LOST')
