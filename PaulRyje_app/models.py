from datetime import timedelta

from django.db import models
from django.utils import timezone


class Book(models.Model):
    STATUS_CHOICES = [
        ('Available', 'Available'),
        ('Checked Out', 'Checked Out'),
        ('Reserved', 'Reserved'),
        ('Lost', 'Lost'),
    ]

    title = models.CharField(max_length=200)
    author = models.CharField(max_length=200)
    isbn = models.CharField(max_length=20, blank=True, null=True)
    genre = models.CharField(max_length=100, blank=True, null=True)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='Available')

    # Bootstrap colour name for each status, used by the status pills
    STATUS_BADGE = {
        'Available': 'success',
        'Checked Out': 'warning',
        'Reserved': 'info',
        'Lost': 'danger',
    }

    class Meta:
        ordering = ['title', 'id']

    @property
    def badge_class(self):
        return self.STATUS_BADGE.get(self.status, 'secondary')

    @property
    def is_available(self):
        return self.status == 'Available'

    def __str__(self):
        return self.title


class Member(models.Model):
    STATUS_CHOICES = [
        ('Active', 'Active'),
        ('Suspended', 'Suspended'),
        ('Inactive', 'Inactive'),
    ]

    STATUS_BADGE = {
        'Active': 'success',
        'Suspended': 'warning',
        'Inactive': 'secondary',
    }

    full_name = models.CharField(max_length=200)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=30, blank=True)
    address = models.TextField(blank=True)
    joined_on = models.DateField(default=timezone.localdate)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Active')

    class Meta:
        ordering = ['full_name', 'id']

    @property
    def badge_class(self):
        return self.STATUS_BADGE.get(self.status, 'secondary')

    @property
    def active_borrowings(self):
        return self.borrowings.filter(returned_on__isnull=True)

    @property
    def active_borrow_count(self):
        return self.active_borrowings.count()

    @property
    def can_borrow(self):
        return self.status == 'Active'

    def __str__(self):
        return self.full_name


class Borrowing(models.Model):
    member = models.ForeignKey(Member, on_delete=models.PROTECT, related_name='borrowings')
    book = models.ForeignKey(Book, on_delete=models.PROTECT, related_name='borrowings')
    borrowed_on = models.DateField(default=timezone.localdate)
    due_on = models.DateField(blank=True, null=True)
    returned_on = models.DateField(blank=True, null=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-borrowed_on', '-id']

    @property
    def is_returned(self):
        return self.returned_on is not None

    @property
    def is_overdue(self):
        return not self.is_returned and self.due_on is not None and self.due_on < timezone.localdate()

    @property
    def days_overdue(self):
        if not self.is_overdue:
            return 0
        return (timezone.localdate() - self.due_on).days

    @property
    def status(self):
        if self.is_returned:
            return 'Returned'
        if self.is_overdue:
            return 'Overdue'
        return 'Borrowed'

    @property
    def badge_class(self):
        return {
            'Returned': 'secondary',
            'Overdue': 'danger',
            'Borrowed': 'warning',
        }.get(self.status, 'secondary')

    def save(self, *args, **kwargs):
        if self.due_on is None:
            loan_days = LibrarySettings.get_solo().loan_period_days
            self.due_on = self.borrowed_on + timedelta(days=loan_days)
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.book.title} - {self.member.full_name}'


class LibrarySettings(models.Model):
    library_name = models.CharField(max_length=150, default='HANTICA Library')
    branch = models.CharField(max_length=150, blank=True)
    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=30, blank=True)
    address = models.TextField(blank=True)
    loan_period_days = models.PositiveIntegerField(default=14)
    max_books_per_member = models.PositiveIntegerField(default=3)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Library Settings'
        verbose_name_plural = 'Library Settings'

    @classmethod
    def get_solo(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    def __str__(self):
        return self.library_name
