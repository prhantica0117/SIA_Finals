from django import forms

from .models import Book, Borrowing, LibrarySettings, Member


class BootstrapFormMixin:
    """Apply the shared Bootstrap classes to every widget in a form."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field in self.fields.values():
            widget = field.widget

            if isinstance(widget, forms.CheckboxInput):
                css_class = 'form-check-input'
            elif isinstance(widget, (forms.Select, forms.SelectMultiple)):
                css_class = 'form-select'
            else:
                css_class = 'form-control'

            existing = widget.attrs.get('class', '')
            widget.attrs['class'] = f'{existing} {css_class}'.strip()

            if isinstance(widget, forms.DateTimeInput):
                widget.input_type = 'datetime-local'
            elif isinstance(widget, forms.DateInput):
                widget.input_type = 'date'
            elif isinstance(widget, (forms.TextInput, forms.EmailInput, forms.NumberInput, forms.Textarea)):
                widget.attrs.setdefault('placeholder', field.label)


class BookForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Book
        fields = ['title', 'author', 'isbn', 'genre', 'status']
        widgets = {
            'title': forms.TextInput(attrs={'placeholder': 'e.g. Things Fall Apart'}),
            'author': forms.TextInput(attrs={'placeholder': 'e.g. Chinua Achebe'}),
            'isbn': forms.TextInput(attrs={'placeholder': 'e.g. 978-0-385-47454-2'}),
            'genre': forms.TextInput(attrs={'placeholder': 'e.g. Fiction, Science, History'}),
        }


class MemberForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Member
        fields = ['full_name', 'email', 'phone', 'address', 'joined_on', 'status']
        widgets = {
            'full_name': forms.TextInput(attrs={'placeholder': 'e.g. Maria Santos'}),
            'email': forms.EmailInput(attrs={'placeholder': 'e.g. maria@example.com'}),
            'phone': forms.TextInput(attrs={'placeholder': 'e.g. 0917 123 4567'}),
            'address': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Optional home address'}),
        }


class BorrowingForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Borrowing
        fields = ['member', 'book', 'borrowed_on', 'notes']
        widgets = {
            'borrowed_on': forms.DateInput(format='%Y-%m-%d'),
            'notes': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Optional notes about this borrowing'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['member'].queryset = Member.objects.filter(status='Active')
        self.fields['book'].queryset = Book.objects.filter(status='Available')
        self.fields['member'].empty_label = 'Select an active member'
        self.fields['book'].empty_label = 'Select an available book'

    def clean(self):
        cleaned_data = super().clean()
        member = cleaned_data.get('member')
        book = cleaned_data.get('book')

        if member and member.status != 'Active':
            self.add_error('member', 'Only active members can borrow books.')

        if book and book.status != 'Available':
            self.add_error('book', f'"{book.title}" is not available for borrowing right now.')

        if member and book:
            library = LibrarySettings.get_solo()
            active_count = member.borrowings.filter(returned_on__isnull=True).count()
            if active_count >= library.max_books_per_member:
                self.add_error(
                    'member',
                    f'{member.full_name} already has {active_count} active borrowing(s). '
                    f'The limit is {library.max_books_per_member}.',
                )

        return cleaned_data


class LibrarySettingsForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = LibrarySettings
        fields = [
            'library_name',
            'branch',
            'contact_email',
            'contact_phone',
            'address',
            'loan_period_days',
            'max_books_per_member',
        ]
        widgets = {
            'library_name': forms.TextInput(attrs={'placeholder': 'e.g. HANTICA Library'}),
            'branch': forms.TextInput(attrs={'placeholder': 'e.g. Main Branch'}),
            'contact_email': forms.EmailInput(attrs={'placeholder': 'e.g. library@example.com'}),
            'contact_phone': forms.TextInput(attrs={'placeholder': 'e.g. (02) 8123 4567'}),
            'address': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Library address'}),
            'loan_period_days': forms.NumberInput(attrs={'min': 1}),
            'max_books_per_member': forms.NumberInput(attrs={'min': 1}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['loan_period_days'].help_text = 'Number of days a member may keep a borrowed book.'
        self.fields['max_books_per_member'].help_text = 'Maximum number of books one member may borrow at a time.'

    def clean_loan_period_days(self):
        value = self.cleaned_data['loan_period_days']
        if value < 1:
            raise forms.ValidationError('The loan period must be at least 1 day.')
        return value

    def clean_max_books_per_member(self):
        value = self.cleaned_data['max_books_per_member']
        if value < 1:
            raise forms.ValidationError('The borrowing limit must be at least 1 book.')
        return value
