import os

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'MyProject.settings')
django.setup()

from datetime import timedelta
from html.parser import HTMLParser

from django.conf import settings
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from PaulRyje_app.models import Book, Borrowing, LibrarySettings, Member

settings.ALLOWED_HOSTS = ['testserver']

client = Client()

PAGES = [
    ('dashboard', 'Dashboard'),
    ('book_catalog', 'Book Catalog'),
    ('member_list', 'Members'),
    ('borrowing_list', 'Borrowing'),
    ('reports', 'Reports'),
    ('library_settings', 'Settings'),
]

NAV_LABELS = ['Dashboard', 'Book Catalog', 'Members', 'Borrowing', 'Reports', 'Settings']

created_books = []
created_members = []
created_borrowings = []

settings_existed = LibrarySettings.objects.exists()
original_settings = None
if settings_existed:
    original_settings = LibrarySettings.get_solo()

loan_days = LibrarySettings.get_solo().loan_period_days


class TagBalance(HTMLParser):
    """Flags unclosed or mismatched tags in rendered HTML."""

    void = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input',
            'link', 'meta', 'param', 'source', 'track', 'wbr'}

    def __init__(self):
        super().__init__()
        self.stack = []
        self.errors = []

    def handle_starttag(self, tag, attrs):
        if tag not in self.void:
            self.stack.append(tag)

    def handle_startendtag(self, tag, attrs):
        pass

    def handle_endtag(self, tag):
        if not self.stack:
            self.errors.append('stray </%s>' % tag)
        elif self.stack[-1] == tag:
            self.stack.pop()
        else:
            self.errors.append('</%s> closes <%s>' % (tag, self.stack[-1]))


def page_ok(name, label):
    response = client.get(reverse(name))
    html = response.content.decode()
    nav_ok = all(item in html for item in NAV_LABELS)
    links_ok = all(reverse(link) in html for link in
                   ['dashboard', 'book_catalog', 'member_list', 'borrowing_list', 'reports', 'library_settings'])
    parser = TagBalance()
    parser.feed(html)
    balanced = not (parser.errors or parser.stack)

    print(f'{label:<16} status={response.status_code} nav={nav_ok} links={links_ok} tags={balanced}')
    if parser.errors:
        print('  tag errors:', parser.errors[:4])
    if parser.stack:
        print('  unclosed:', parser.stack[:4])


try:
    print('--- Pages and navigation ---')
    for name, label in PAGES:
        page_ok(name, label)

    print('--- Modal markup ---')
    catalog_html = client.get(reverse('book_catalog')).content.decode()
    member_html = client.get(reverse('member_list')).content.decode()
    borrowing_html = client.get(reverse('borrowing_list')).content.decode()
    print('catalog modals   :', all(item in catalog_html for item in
                                  ['bookAddModal', 'bookEditModal', 'bookDeleteModal']))
    print('member modals    :', all(item in member_html for item in
                                  ['memberAddModal', 'memberEditModal', 'memberDeleteModal']))
    print('borrowing modals :', all(item in borrowing_html for item in
                                  ['borrowingAddModal', 'returnModal']))
    print('modal triggers   :', all('data-bs-toggle="modal"' in html for html in
                                  [catalog_html, member_html, borrowing_html]))
    invalid_add = client.post(reverse('book_create'), {
        'add-title': '',
        'add-author': '',
        'add-status': 'Available',
    })
    print('invalid add modal:', invalid_add.status_code == 200
          and 'data-auto-modal="bookAddModal"' in invalid_add.content.decode())

    print('--- Create member ---')
    member_name = f'Verify Member {timezone.now():%H%M%S}'
    response = client.post(reverse('member_create'), {
        'add-full_name': member_name,
        'add-email': 'verify@example.com',
        'add-phone': '0917 000 0000',
        'add-address': 'Verification Address',
        'add-joined_on': timezone.localdate().isoformat(),
        'add-status': 'Active',
    })
    member = Member.objects.filter(full_name=member_name).first()
    if member:
        created_members.append(member.pk)
    print('member created   :', bool(member), '| redirect:', response.status_code)

    print('--- Create book ---')
    book_title = f'Verify Book {timezone.now():%H%M%S}'
    response = client.post(reverse('book_create'), {
        'add-title': book_title,
        'add-author': 'Verify Author',
        'add-isbn': '978-0-00-000000-0',
        'add-genre': 'Verification',
        'add-status': 'Available',
    })
    book = Book.objects.filter(title=book_title).first()
    if book:
        created_books.append(book.pk)
    print('book created     :', bool(book), '| redirect:', response.status_code)

    print('--- Create borrowing ---')
    response = client.post(reverse('borrowing_create'), {
        'borrow-member': member.pk if member else 0,
        'borrow-book': book.pk if book else 0,
        'borrow-borrowed_on': timezone.localdate().isoformat(),
        'borrow-notes': 'Verification borrowing',
    })
    borrowing = Borrowing.objects.filter(book=book).first() if book else None
    if borrowing:
        created_borrowings.append(borrowing.pk)
    if book:
        book.refresh_from_db()
    print('borrowing created:', bool(borrowing), '| redirect:', response.status_code)
    print('book checked out :', bool(book) and book.status == 'Checked Out')
    print('due date set     :', bool(borrowing) and borrowing.due_on == timezone.localdate() + timedelta(days=loan_days))
    print('loan is not money:', bool(borrowing) and not hasattr(borrowing, 'amount'))

    print('--- Search and reports ---')
    html = client.get(reverse('book_catalog'), {'q': book_title}).content.decode()
    print('catalog search   :', book_title in html)
    html = client.get(reverse('member_list'), {'q': member_name}).content.decode()
    print('member search    :', member_name in html)
    html = client.get(reverse('reports')).content.decode()
    print('report book      :', book_title in html)
    print('report member    :', member_name in html)
    print('report overdue   :', 'Overdue Items' in html)

    print('--- Return borrowing ---')
    response = client.post(reverse('borrowing_return', args=[borrowing.pk]))
    borrowing.refresh_from_db()
    book.refresh_from_db()
    print('return redirect  :', response.status_code == 302)
    print('returned date    :', borrowing.returned_on == timezone.localdate())
    print('book available   :', book.status == 'Available')

    print('--- Settings ---')
    response = client.post(reverse('library_settings'), {
        'library_name': 'Verify Library',
        'branch': 'Verify Branch',
        'contact_email': 'verify@example.com',
        'contact_phone': '02 8000 0000',
        'address': 'Verify Address',
        'loan_period_days': 21,
        'max_books_per_member': 5,
    })
    library = LibrarySettings.get_solo()
    print('settings saved   :', response.status_code == 302 and library.loan_period_days == 21)
    print('settings values  :', library.library_name == 'Verify Library' and library.max_books_per_member == 5)

    print('--- Delete protection with borrowing history ---')
    client.post(reverse('book_delete', args=[book.pk]))
    client.post(reverse('member_delete', args=[member.pk]))
    print('book protected   :', Book.objects.filter(pk=book.pk).exists())
    print('member protected :', Member.objects.filter(pk=member.pk).exists())

    print('--- Cleanup and delete flow ---')
    Borrowing.objects.filter(pk__in=created_borrowings).delete()
    created_borrowings.clear()
    response = client.post(reverse('book_delete', args=[book.pk]))
    print('book deleted     :', response.status_code == 302 and not Book.objects.filter(pk=book.pk).exists())
    response = client.post(reverse('member_delete', args=[member.pk]))
    print('member deleted   :', response.status_code == 302 and not Member.objects.filter(pk=member.pk).exists())
    created_books.clear()
    created_members.clear()

finally:
    Borrowing.objects.filter(pk__in=created_borrowings).delete()
    Book.objects.filter(pk__in=created_books).delete()
    Member.objects.filter(pk__in=created_members).delete()

    if settings_existed and original_settings:
        LibrarySettings.objects.filter(pk=1).update(
            library_name=original_settings.library_name,
            branch=original_settings.branch,
            contact_email=original_settings.contact_email,
            contact_phone=original_settings.contact_phone,
            address=original_settings.address,
            loan_period_days=original_settings.loan_period_days,
            max_books_per_member=original_settings.max_books_per_member,
        )
    elif not settings_existed:
        LibrarySettings.objects.filter(pk=1).delete()

    print('--- Final database state ---')
    print('books            :', Book.objects.count())
    print('members          :', Member.objects.count())
    print('borrowings       :', Borrowing.objects.count())
    print('settings rows    :', LibrarySettings.objects.count())
