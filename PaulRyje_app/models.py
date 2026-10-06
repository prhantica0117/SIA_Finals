from django.db import models

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

    # Bootstrap colour name for each status, used by the dashboard status pill
    STATUS_BADGE = {
        'Available': 'success',
        'Checked Out': 'warning',
        'Reserved': 'info',
        'Lost': 'danger',
    }

    @property
    def badge_class(self):
        return self.STATUS_BADGE.get(self.status, 'secondary')

    def __str__(self):
        return self.title