import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'MyProject.settings')
django.setup()
from django.conf import settings
settings.ALLOWED_HOSTS = ['testserver']

from django.test import Client
from django.urls import reverse
from PaulRyje_app.models import Book

c = Client()
url = reverse('dashboard')
before = Book.objects.count()

print('--- GET dashboard ---')
r = c.get(url)
html = r.content.decode()
print('status 200          :', r.status_code)
print('sidebar + brand     :', 'sidebar' in html and 'HANTICA' in html)
print('bootstrap + icons   :', 'bootstrap.bundle.min.js' in html and 'bootstrap-icons' in html)
print('add button wired    :', 'data-bs-target="#addBookModal"' in html)
print('csrf token          :', 'csrfmiddlewaretoken' in html)
print('modal fields        :', all(i in html for i in ['id_title', 'id_author', 'id_isbn', 'id_genre', 'id_status']))
print('summary cards (4)   :', html.count('class="stat-card') == 4)
print('modal starts closed :', 'data-reopen="0"' in html)

print('--- invalid POST (blank required fields) ---')
r = c.post(url, {'title': '', 'author': '', 'isbn': '', 'genre': '', 'status': 'Available'})
html = r.content.decode()
print('status 200          :', r.status_code)
print('modal reopens       :', 'data-reopen="1"' in html)
print('nothing written     :', Book.objects.count() == before)
print('danger banner       :', 'alert-danger' in html and 'was not saved' in html)
print('field errors shown  :', 'errorlist' in html)

print('--- invalid POST (status outside Book.STATUS_CHOICES) ---')
r = c.post(url, {'title': 'X', 'author': 'Y', 'status': 'Nonsense'})
print('rejected            :', Book.objects.count() == before and 'Select a valid choice' in r.content.decode())

print('--- valid POST writes to the database ---')
r = c.post(url, {'title': 'Smoke Test Book', 'author': 'Jane Doe', 'isbn': '978-0-00-000000-1',
                 'genre': 'Test', 'status': 'Checked Out'}, follow=True)
html = r.content.decode()
book = Book.objects.filter(title='Smoke Test Book').first()
print('redirect + render   :', r.status_code)
print('row in database     :', bool(book), '| status:', book.status if book else '-')
print('row in table        :', 'Smoke Test Book' in html)
print('status pill         :', 'badge-status' in html and 'bg-warning-subtle' in html)
print('success banner      :', 'alert-success' in html and 'added to the inventory' in html)
print('modal closed again  :', 'data-reopen="1"' not in html)

print('--- dashboard reads live figures from the database ---')
print('total count live    :', '<div class="stat-value">%d<' % Book.objects.count() in html)
print('checked out live    :', '<div class="stat-value">%d<' % Book.objects.filter(status='Checked Out').count() in html)

print('--- search filters the queryset ---')
print('search by author    :', 'Smoke Test Book' in c.get(url, {'q': 'jane doe'}).content.decode())
print('search by isbn      :', 'Smoke Test Book' in c.get(url, {'q': '978-0-00'}).content.decode())
print('unmatched search    :', 'Smoke Test Book' not in c.get(url, {'q': 'no-such-book-zzz'}).content.decode())
print('search term kept    :', 'no-such-book-zzz' in c.get(url, {'q': 'no-such-book-zzz'}).content.decode())

book.delete()
print('cleanup ok          :', Book.objects.count() == before)

print('--- CSRF protection ---')
import re
csrf_client = Client(enforce_csrf_checks=True)
html = csrf_client.get(url).content.decode()
r = csrf_client.post(url, {'title': 'No Token', 'author': 'X', 'status': 'Available'})
print('POST without token  :', r.status_code == 403)
token = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', html).group(1)
csrf_client.post(url, {'title': 'Csrf Book', 'author': 'X', 'status': 'Available',
                       'csrfmiddlewaretoken': token}, follow=True)
print('POST with token     :', Book.objects.filter(title='Csrf Book').exists())
Book.objects.filter(title='Csrf Book').delete()
print('database clean      :', Book.objects.count() == before)

print('--- rendered markup is well formed ---')
from html.parser import HTMLParser


class TagBalance(HTMLParser):
    """Flags unclosed / mismatched tags in the rendered dashboard."""

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
        pass  # self closing, nothing to check

    def handle_endtag(self, tag):
        if not self.stack:
            self.errors.append('stray </%s>' % tag)
        elif self.stack[-1] == tag:
            self.stack.pop()
        else:
            self.errors.append('</%s> closes <%s>' % (tag, self.stack[-1]))


parser = TagBalance()
parser.feed(c.get(url).content.decode())
problems = parser.errors + ['unclosed <%s>' % t for t in parser.stack]
print('tags balanced       :', not problems, problems[:4])
