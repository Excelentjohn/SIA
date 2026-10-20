from datetime import date
from tempfile import TemporaryDirectory

from django.test import TestCase, override_settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.contrib.auth.models import User
from django.utils import timezone

from .models import LostFound, Category, Location, ArchiveProfile


class DashboardViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='archive-user', password='test-password-123')
        self.client.force_login(self.user)
        Category.objects.create(name='Bag')
        Location.objects.create(name='Library')
        Location.objects.create(name='Science Hall')
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

    def test_category_added_is_persisted_and_shown_on_dashboard(self):
        response = self.client.post(reverse('categories'), {'name': 'Books'}, follow=True)
        self.assertContains(response, 'Category added.')
        self.assertTrue(Category.objects.filter(name='Books').exists())
        dashboard = self.client.get(reverse('dashboard'))
        self.assertContains(dashboard, 'Books')

    def test_all_and_status_category_location_search_filters(self):
        cases = [
            ({'category': 'all', 'location': 'all'}, {'Black Backpack', 'Silver Key'}),
            ({'status': 'Found'}, {'Black Backpack'}),
            ({'category': 'BAGS'}, {'Black Backpack'}),
            ({'location': 'Library'}, {'Black Backpack'}),
            ({'search': 'Silver'}, {'Silver Key'}),
            ({'status': 'lost', 'category': 'KEYS', 'location': 'Science Hall'}, {'Silver Key'}),
            ({'status': 'not-a-status', 'category': 'unknown', 'location': 'unknown'}, {'Black Backpack', 'Silver Key'}),
        ]
        for params, expected in cases:
            with self.subTest(params=params):
                response = self.client.get(reverse('dashboard'), params)
                self.assertEqual(response.status_code, 200)
                self.assertEqual({item.item_name for item in response.context['items']}, expected)

    def test_status_filter_controls_are_links_and_show_the_selected_filter(self):
        all_response = self.client.get(reverse('dashboard'))
        self.assertContains(all_response, 'class="filter-btn active"')
        for status in ('Lost', 'Found', 'Claimed', 'Pending'):
            with self.subTest(status=status):
                response = self.client.get(reverse('dashboard'), {'status': status})
                self.assertEqual(response.context['status_filter'], status)
                self.assertContains(response, f'href="?status={status}')
                self.assertContains(response, f'class="filter-btn active" href="?status={status}')

    def test_lost_found_and_cases_have_scoped_working_lists(self):
        lost_response = self.client.get(reverse('item_list', args=['lost']))
        self.assertContains(lost_response, 'Lost Items')
        self.assertContains(lost_response, 'Silver Key')
        self.assertNotContains(lost_response, 'Black Backpack')

        found_response = self.client.get(reverse('item_list', args=['found']), {'search': 'black', 'category': 'BAGS'})
        self.assertContains(found_response, 'Black Backpack')
        self.assertNotContains(found_response, 'Silver Key')

        cases_response = self.client.get(reverse('cases'))
        self.assertContains(cases_response, 'Cases')
        self.assertContains(cases_response, 'Black Backpack')
        self.assertContains(cases_response, 'Silver Key')

    def test_item_report_links_preselect_lost_or_found_status(self):
        lost_form = self.client.get(reverse('item_create'), {'status': 'Lost'})
        self.assertEqual(lost_form.context['form']['status'].value(), 'Lost')
        found_form = self.client.get(reverse('item_create'), {'status': 'Found'})
        self.assertEqual(found_form.context['form']['status'].value(), 'Found')

    def test_dashboard_statistics_are_database_counts(self):
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.context['total_items'], 2)
        self.assertEqual(response.context['case_files'], 2)
        self.assertEqual(response.context['lost_items'], 1)
        self.assertEqual(response.context['found_items'], 1)
        self.assertEqual(response.context['claimed_items'], 0)
        self.assertEqual(response.context['active_cases'], 2)

    def test_creating_lost_item_increases_total_case_file_and_lost_counts(self):
        response = self.client.post(reverse('item_create'), {
            'item_name': 'Blue Umbrella', 'description': 'Left near the entrance.',
            'category': 'Umbrellas', 'location': 'Main Hall', 'date': '2026-10-20',
            'status': 'Lost', 'owner_name': 'Archive User',
        })
        self.assertEqual(response.status_code, 302)
        stats = self.client.get(reverse('dashboard')).context
        self.assertEqual(stats['total_items'], 3)
        self.assertEqual(stats['case_files'], 3)
        self.assertEqual(stats['lost_items'], 2)

    def test_lost_to_found_to_claimed_updates_existing_record_and_statistics(self):
        item = LostFound.objects.get(item_name='Silver Key')
        total_before = LostFound.objects.count()
        response = self.client.post(reverse('transition_case', args=[item.pk, 'Found']), follow=True)
        item.refresh_from_db()
        self.assertContains(response, 'Item marked as found.')
        self.assertEqual(item.status, 'Found')
        self.assertEqual(item.date_found, timezone.localdate())
        self.assertEqual(item.found_by, self.user.username)
        self.assertEqual(LostFound.objects.count(), total_before)
        stats = self.client.get(reverse('dashboard')).context
        self.assertEqual(stats['total_items'], 2)
        self.assertEqual(stats['lost_items'], 0)
        self.assertEqual(stats['found_items'], 2)
        self.assertEqual(stats['active_cases'], 2)

        response = self.client.post(reverse('transition_case', args=[item.pk, 'Claimed']), follow=True)
        item.refresh_from_db()
        self.assertContains(response, 'Recovery confirmed.')
        self.assertEqual(item.status, 'Claimed')
        self.assertEqual(LostFound.objects.count(), total_before)
        stats = self.client.get(reverse('dashboard')).context
        self.assertEqual(stats['claimed_items'], 1)
        self.assertEqual(stats['active_cases'], 1)

    def test_invalid_status_transition_does_not_change_record(self):
        item = LostFound.objects.get(item_name='Silver Key')
        response = self.client.post(reverse('transition_case', args=[item.pk, 'Claimed']), follow=True)
        self.assertContains(response, 'Cannot change this record')
        item.refresh_from_db()
        self.assertEqual(item.status, 'LOST')

    def test_status_transition_requires_login_and_post(self):
        item = LostFound.objects.get(item_name='Silver Key')
        url = reverse('transition_case', args=[item.pk, 'Found'])
        self.assertEqual(self.client.get(url).status_code, 405)
        self.client.logout()
        self.assertEqual(self.client.post(url).status_code, 302)

    def test_profile_page_saves_details_and_profile_photo(self):
        with TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root):
            image = SimpleUploadedFile(
                'archive-avatar.png',
                b'\x89PNG\r\n\x1a\n' + b'\x00' * 16,
                content_type='image/png',
            )
            response = self.client.post(reverse('profile'), {
                'user-first_name': 'Archive', 'user-last_name': 'Member', 'user-email': 'member@example.com',
                'archive-bio': 'Helping reunite people with their belongings.', 'archive-photo': image,
            }, follow=True)
            self.assertContains(response, 'Your archive profile has been updated.')
            self.user.refresh_from_db()
            self.assertEqual(self.user.first_name, 'Archive')
            profile = ArchiveProfile.objects.get(user=self.user)
            self.assertEqual(profile.bio, 'Helping reunite people with their belongings.')
            self.assertTrue(profile.photo.name.endswith('archive-avatar.png'))
