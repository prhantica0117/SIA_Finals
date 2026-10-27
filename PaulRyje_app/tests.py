from datetime import timedelta

from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Book, Borrowing, LibrarySettings, Member


class NavigationTests(TestCase):
    def test_all_pages_render_with_navigation(self):
        pages = [
            'dashboard',
            'book_catalog',
            'member_list',
            'borrowing_list',
            'reports',
            'library_settings',
        ]

        for name in pages:
            response = self.client.get(reverse(name))
            self.assertEqual(response.status_code, 200, name)
            self.assertContains(response, 'Book Catalog')
            self.assertContains(response, 'Members')
            self.assertContains(response, 'Borrowing')
            self.assertContains(response, 'Reports')
            self.assertContains(response, 'Settings')
            self.assertContains(response, reverse('book_catalog'))
            self.assertContains(response, reverse('member_list'))
            self.assertContains(response, reverse('borrowing_list'))
            self.assertContains(response, reverse('reports'))
            self.assertContains(response, reverse('library_settings'))


class CsrfTests(TestCase):
    def test_post_without_csrf_token_is_rejected(self):
        client = Client(enforce_csrf_checks=True)
        response = client.post(reverse('book_create'), {
            'title': 'No Token',
            'author': 'No Author',
            'status': 'Available',
        })
        self.assertEqual(response.status_code, 403)


class FormPageTests(TestCase):
    def setUp(self):
        self.book = Book.objects.create(
            title='Test Book',
            author='Test Author',
            status='Available',
        )
        self.member = Member.objects.create(
            full_name='Test Member',
            status='Active',
        )

    def test_form_and_confirm_pages_render(self):
        urls = [
            reverse('book_create'),
            reverse('book_update', args=[self.book.pk]),
            reverse('book_delete', args=[self.book.pk]),
            reverse('member_create'),
            reverse('member_update', args=[self.member.pk]),
            reverse('member_delete', args=[self.member.pk]),
            reverse('borrowing_create'),
        ]

        for url in urls:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200, url)


class ModalTests(TestCase):
    def setUp(self):
        self.book = Book.objects.create(
            title='Modal Book',
            author='Modal Author',
            status='Available',
        )
        self.member = Member.objects.create(
            full_name='Modal Member',
            status='Active',
        )

    def test_modal_markup_is_present(self):
        catalog = self.client.get(reverse('book_catalog'))
        self.assertContains(catalog, 'id="bookAddModal"')
        self.assertContains(catalog, 'id="bookEditModal"')
        self.assertContains(catalog, 'id="bookDeleteModal"')

        members = self.client.get(reverse('member_list'))
        self.assertContains(members, 'id="memberAddModal"')
        self.assertContains(members, 'id="memberEditModal"')
        self.assertContains(members, 'id="memberDeleteModal"')

        borrowing = self.client.get(reverse('borrowing_list'))
        self.assertContains(borrowing, 'id="borrowingAddModal"')
        self.assertContains(borrowing, 'id="returnModal"')

    def test_invalid_add_reopens_add_modal(self):
        response = self.client.post(reverse('book_create'), {
            'add-title': '',
            'add-author': '',
            'add-status': 'Available',
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-auto-modal="bookAddModal"')
        self.assertContains(response, 'errorlist')

    def test_invalid_edit_reopens_edit_modal(self):
        response = self.client.post(reverse('book_update', args=[self.book.pk]), {
            'edit-title': '',
            'edit-author': '',
            'edit-status': 'Available',
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-auto-modal="bookEditModal"')
        self.assertContains(response, 'errorlist')

    def test_direct_edit_url_opens_prefilled_modal(self):
        response = self.client.get(reverse('book_update', args=[self.book.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-auto-modal="bookEditModal"')
        self.assertContains(response, 'data-preserve="1"')
        self.assertContains(response, 'Modal Book')


class BookTests(TestCase):
    def setUp(self):
        self.book = Book.objects.create(
            title='Things Fall Apart',
            author='Chinua Achebe',
            isbn='978-0-385-47454-2',
            genre='Fiction',
        )

    def test_create_book(self):
        response = self.client.post(reverse('book_create'), {
            'add-title': 'Purple Hibiscus',
            'add-author': 'Chimamanda Ngozi Adichie',
            'add-isbn': '978-1-61620-242-2',
            'add-genre': 'Fiction',
            'add-status': 'Available',
        })
        self.assertRedirects(response, reverse('book_catalog'))
        self.assertTrue(Book.objects.filter(title='Purple Hibiscus').exists())

    def test_search_and_status_filter(self):
        row = '<span class="book-title">Things Fall Apart</span>'
        response = self.client.get(reverse('book_catalog'), {'q': 'achebe'})
        self.assertContains(response, row)

        response = self.client.get(reverse('book_catalog'), {'status': 'Lost'})
        self.assertNotContains(response, row)

    def test_edit_book(self):
        response = self.client.post(reverse('book_update', args=[self.book.pk]), {
            'edit-title': 'Things Fall Apart (Revised)',
            'edit-author': 'Chinua Achebe',
            'edit-isbn': '978-0-385-47454-2',
            'edit-genre': 'Fiction',
            'edit-status': 'Reserved',
        })
        self.assertRedirects(response, reverse('book_catalog'))
        self.book.refresh_from_db()
        self.assertEqual(self.book.title, 'Things Fall Apart (Revised)')
        self.assertEqual(self.book.status, 'Reserved')

    def test_delete_book(self):
        response = self.client.post(reverse('book_delete', args=[self.book.pk]))
        self.assertRedirects(response, reverse('book_catalog'))
        self.assertFalse(Book.objects.filter(pk=self.book.pk).exists())


class MemberTests(TestCase):
    def setUp(self):
        self.member = Member.objects.create(
            full_name='Maria Santos',
            email='maria@example.com',
            phone='0917 123 4567',
        )

    def test_create_member(self):
        response = self.client.post(reverse('member_create'), {
            'add-full_name': 'Juan Dela Cruz',
            'add-email': 'juan@example.com',
            'add-phone': '0918 765 4321',
            'add-address': 'Manila',
            'add-joined_on': timezone.localdate().isoformat(),
            'add-status': 'Active',
        })
        self.assertRedirects(response, reverse('member_list'))
        self.assertTrue(Member.objects.filter(full_name='Juan Dela Cruz').exists())

    def test_search_member(self):
        response = self.client.get(reverse('member_list'), {'q': 'maria'})
        self.assertContains(response, 'Maria Santos')

    def test_edit_member(self):
        response = self.client.post(reverse('member_update', args=[self.member.pk]), {
            'edit-full_name': 'Maria Santos-Cruz',
            'edit-email': 'maria@example.com',
            'edit-phone': '0917 123 4567',
            'edit-address': '',
            'edit-joined_on': self.member.joined_on.isoformat(),
            'edit-status': 'Active',
        })
        self.assertRedirects(response, reverse('member_list'))
        self.member.refresh_from_db()
        self.assertEqual(self.member.full_name, 'Maria Santos-Cruz')

    def test_delete_member(self):
        response = self.client.post(reverse('member_delete', args=[self.member.pk]))
        self.assertRedirects(response, reverse('member_list'))
        self.assertFalse(Member.objects.filter(pk=self.member.pk).exists())


class BorrowingTests(TestCase):
    def setUp(self):
        self.library = LibrarySettings.get_solo()
        self.library.loan_period_days = 14
        self.library.max_books_per_member = 2
        self.library.save()

        self.book = Book.objects.create(
            title='Half of a Yellow Sun',
            author='Chimamanda Ngozi Adichie',
            status='Available',
        )
        self.member = Member.objects.create(
            full_name='Ana Reyes',
            status='Active',
        )

    def test_borrow_sets_due_date_and_book_status(self):
        today = timezone.localdate()
        response = self.client.post(reverse('borrowing_create'), {
            'borrow-member': self.member.pk,
            'borrow-book': self.book.pk,
            'borrow-borrowed_on': today.isoformat(),
            'borrow-notes': '',
        })
        self.assertRedirects(response, reverse('borrowing_list'))

        borrowing = Borrowing.objects.get()
        self.assertEqual(borrowing.due_on, today + timedelta(days=14))
        self.book.refresh_from_db()
        self.assertEqual(self.book.status, 'Checked Out')

    def test_return_restores_available_status(self):
        borrowing = Borrowing.objects.create(
            member=self.member,
            book=self.book,
            borrowed_on=timezone.localdate(),
        )
        self.book.status = 'Checked Out'
        self.book.save(update_fields=['status'])

        response = self.client.post(reverse('borrowing_return', args=[borrowing.pk]))
        self.assertRedirects(response, reverse('borrowing_list'))

        borrowing.refresh_from_db()
        self.book.refresh_from_db()
        self.assertEqual(borrowing.returned_on, timezone.localdate())
        self.assertEqual(self.book.status, 'Available')

    def test_overdue_status(self):
        today = timezone.localdate()
        borrowing = Borrowing.objects.create(
            member=self.member,
            book=self.book,
            borrowed_on=today - timedelta(days=20),
            due_on=today - timedelta(days=6),
        )
        self.assertTrue(borrowing.is_overdue)
        self.assertEqual(borrowing.status, 'Overdue')
        self.assertEqual(borrowing.days_overdue, 6)

    def test_borrowing_limit_is_enforced(self):
        self.library.max_books_per_member = 1
        self.library.save()

        second_book = Book.objects.create(
            title='Americanah',
            author='Chimamanda Ngozi Adichie',
            status='Available',
        )
        Borrowing.objects.create(
            member=self.member,
            book=self.book,
            borrowed_on=timezone.localdate(),
        )
        self.book.status = 'Checked Out'
        self.book.save(update_fields=['status'])

        response = self.client.post(reverse('borrowing_create'), {
            'borrow-member': self.member.pk,
            'borrow-book': second_book.pk,
            'borrow-borrowed_on': timezone.localdate().isoformat(),
            'borrow-notes': '',
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Borrowing.objects.count(), 1)
        self.assertContains(response, 'The limit is 1')

    def test_unavailable_book_cannot_be_borrowed(self):
        self.book.status = 'Checked Out'
        self.book.save(update_fields=['status'])

        response = self.client.post(reverse('borrowing_create'), {
            'borrow-member': self.member.pk,
            'borrow-book': self.book.pk,
            'borrow-borrowed_on': timezone.localdate().isoformat(),
            'borrow-notes': '',
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Borrowing.objects.count(), 0)

    def test_delete_is_blocked_when_history_exists(self):
        Borrowing.objects.create(
            member=self.member,
            book=self.book,
            borrowed_on=timezone.localdate(),
        )

        self.client.post(reverse('book_delete', args=[self.book.pk]))
        self.client.post(reverse('member_delete', args=[self.member.pk]))

        self.assertTrue(Book.objects.filter(pk=self.book.pk).exists())
        self.assertTrue(Member.objects.filter(pk=self.member.pk).exists())


class SettingsTests(TestCase):
    def test_settings_page_saves_values(self):
        response = self.client.post(reverse('library_settings'), {
            'library_name': 'HANTICA Main Library',
            'branch': 'Main Branch',
            'contact_email': 'library@example.com',
            'contact_phone': '02 8123 4567',
            'address': 'Manila',
            'loan_period_days': 21,
            'max_books_per_member': 5,
        })
        self.assertRedirects(response, reverse('library_settings'))

        library = LibrarySettings.get_solo()
        self.assertEqual(library.library_name, 'HANTICA Main Library')
        self.assertEqual(library.loan_period_days, 21)
        self.assertEqual(library.max_books_per_member, 5)

    def test_settings_rejects_zero_values(self):
        response = self.client.post(reverse('library_settings'), {
            'library_name': 'HANTICA Library',
            'branch': '',
            'contact_email': '',
            'contact_phone': '',
            'address': '',
            'loan_period_days': 0,
            'max_books_per_member': 0,
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'must be at least 1')
