from django import forms
from .models import Book


class BookForm(forms.ModelForm):
    class Meta:
        model = Book
        fields = ['title', 'author', 'isbn', 'genre', 'status']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Things Fall Apart'}),
            'author': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Chinua Achebe'}),
            'isbn': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 978-0-385-47454-2'}),
            'genre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Fiction, Science, History'}),
            # Choices come from Book.STATUS_CHOICES, so the dashboard and the admin
            # always offer the exact same status values.
            'status': forms.Select(attrs={'class': 'form-select'}),
        }
