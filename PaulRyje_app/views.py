from django.contrib import messages
from django.db.models import Count, Q
from django.shortcuts import render, redirect
from .models import Book
from .forms import BookForm


def Home(request):
    if request.method == 'POST':
        form = BookForm(request.POST)
        if form.is_valid():
            book = form.save()  # Writes the new book to the database
            messages.success(request, f'"{book.title}" was added to the inventory.')
            return redirect('dashboard')  # Reload the dashboard with the new row
        messages.error(request, 'The book was not saved. Please check the highlighted fields.')
    else:
        form = BookForm()  # Empty form for the modal

    # Search straight against the database (title, author, ISBN or genre)
    search = request.GET.get('q', '').strip()
    books = Book.objects.all()
    if search:
        books = books.filter(
            Q(title__icontains=search)
            | Q(author__icontains=search)
            | Q(isbn__icontains=search)
            | Q(genre__icontains=search)
        )

    context = {
        'books': books.order_by('-id'),
        'form': form,
        'search': search,
        # Live figures for the summary cards, counted by the database itself
        'stats': Book.objects.aggregate(
            total=Count('id'),
            available=Count('id', filter=Q(status='Available')),
            checked_out=Count('id', filter=Q(status='Checked Out')),
            reserved=Count('id', filter=Q(status='Reserved')),
            lost=Count('id', filter=Q(status='Lost')),
        ),
    }
    return render(request, 'Inv_Books/dashboard.html', context)
