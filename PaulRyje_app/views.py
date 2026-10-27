from django.contrib import messages
from django.db import transaction
from django.db.models import Count, ProtectedError, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import BookForm, BorrowingForm, LibrarySettingsForm, MemberForm
from .models import Book, Borrowing, LibrarySettings, Member


def dashboard(request):
    today = timezone.localdate()

    stats = {
        'books': Book.objects.count(),
        'available': Book.objects.filter(status='Available').count(),
        'checked_out': Book.objects.filter(status='Checked Out').count(),
        'reserved': Book.objects.filter(status='Reserved').count(),
        'members': Member.objects.count(),
        'overdue': Borrowing.objects.filter(returned_on__isnull=True, due_on__lt=today).count(),
    }

    recent_borrowings = (
        Borrowing.objects.select_related('book', 'member')
        .order_by('-borrowed_on', '-id')[:6]
    )
    overdue_borrowings = (
        Borrowing.objects.select_related('book', 'member')
        .filter(returned_on__isnull=True, due_on__lt=today)
        .order_by('due_on')[:5]
    )

    context = {
        'active_section': 'dashboard',
        'stats': stats,
        'recent_borrowings': recent_borrowings,
        'overdue_borrowings': overdue_borrowings,
        'today': today,
    }
    return render(request, 'dashboard/dashboard.html', context)


def _catalog_context(request, add_form=None, edit_form=None, **extra):
    search = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', '').strip()

    valid_statuses = {value for value, _ in Book.STATUS_CHOICES}
    if status_filter not in valid_statuses:
        status_filter = ''

    books = Book.objects.all()
    if search:
        books = books.filter(
            Q(title__icontains=search)
            | Q(author__icontains=search)
            | Q(isbn__icontains=search)
            | Q(genre__icontains=search)
        )
    if status_filter:
        books = books.filter(status=status_filter)

    stats = Book.objects.aggregate(
        total=Count('id'),
        available=Count('id', filter=Q(status='Available')),
        checked_out=Count('id', filter=Q(status='Checked Out')),
        reserved=Count('id', filter=Q(status='Reserved')),
        lost=Count('id', filter=Q(status='Lost')),
    )

    if add_form is None:
        add_form = BookForm(prefix='add')
    if edit_form is None:
        edit_form = BookForm(prefix='edit')

    context = {
        'active_section': 'catalog',
        'books': books,
        'search': search,
        'status_filter': status_filter,
        'status_choices': Book.STATUS_CHOICES,
        'stats': stats,
        'has_filters': bool(search or status_filter),
        'add_form': add_form,
        'edit_form': edit_form,
        'edit_book': None,
        'edit_form_action': '',
        'edit_form_preserve': False,
        'delete_book': None,
        'delete_action': '',
        'delete_preserve': False,
        'open_modal': '',
    }
    context.update(extra)
    return context


def book_catalog(request):
    return render(request, 'catalog/book_catalog.html', _catalog_context(request))


def book_create(request):
    if request.method == 'POST':
        form = BookForm(request.POST, prefix='add')
        if form.is_valid():
            book = form.save()
            messages.success(request, f'"{book.title}" was added to the catalog.')
            return redirect('book_catalog')
        messages.error(request, 'The book was not saved. Please check the highlighted fields.')
        context = _catalog_context(request, add_form=form, open_modal='bookAddModal')
        return render(request, 'catalog/book_catalog.html', context)

    context = _catalog_context(request, open_modal='bookAddModal')
    return render(request, 'catalog/book_catalog.html', context)


def book_update(request, pk):
    book = get_object_or_404(Book, pk=pk)
    action = reverse('book_update', args=[book.pk])

    if request.method == 'POST':
        form = BookForm(request.POST, instance=book, prefix='edit')
        if form.is_valid():
            book = form.save()
            messages.success(request, f'"{book.title}" was updated.')
            return redirect('book_catalog')
        messages.error(request, 'The book was not updated. Please check the highlighted fields.')
        context = _catalog_context(
            request,
            edit_form=form,
            edit_book=book,
            edit_form_action=action,
            edit_form_preserve=True,
            open_modal='bookEditModal',
        )
        return render(request, 'catalog/book_catalog.html', context)

    form = BookForm(instance=book, prefix='edit')
    context = _catalog_context(
        request,
        edit_form=form,
        edit_book=book,
        edit_form_action=action,
        edit_form_preserve=True,
        open_modal='bookEditModal',
    )
    return render(request, 'catalog/book_catalog.html', context)


def book_delete(request, pk):
    book = get_object_or_404(Book, pk=pk)

    if request.method == 'POST':
        title = book.title
        try:
            book.delete()
            messages.success(request, f'"{title}" was removed from the catalog.')
        except ProtectedError:
            messages.error(
                request,
                f'"{title}" cannot be deleted because it has borrowing history. '
                'Keep the record or mark the book as Lost instead.',
            )
        return redirect('book_catalog')

    context = _catalog_context(
        request,
        delete_book=book,
        delete_action=reverse('book_delete', args=[book.pk]),
        delete_preserve=True,
        open_modal='bookDeleteModal',
    )
    return render(request, 'catalog/book_catalog.html', context)


def _member_context(request, add_form=None, edit_form=None, **extra):
    search = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', '').strip()

    valid_statuses = {value for value, _ in Member.STATUS_CHOICES}
    if status_filter not in valid_statuses:
        status_filter = ''

    members = Member.objects.annotate(
        active_count=Count('borrowings', filter=Q(borrowings__returned_on__isnull=True)),
        total_count=Count('borrowings'),
    )
    if search:
        members = members.filter(
            Q(full_name__icontains=search)
            | Q(email__icontains=search)
            | Q(phone__icontains=search)
        )
    if status_filter:
        members = members.filter(status=status_filter)

    if add_form is None:
        add_form = MemberForm(prefix='add')
    if edit_form is None:
        edit_form = MemberForm(prefix='edit')

    context = {
        'active_section': 'members',
        'members': members,
        'search': search,
        'status_filter': status_filter,
        'status_choices': Member.STATUS_CHOICES,
        'has_filters': bool(search or status_filter),
        'stats': {
            'total': Member.objects.count(),
            'active': Member.objects.filter(status='Active').count(),
            'suspended': Member.objects.filter(status='Suspended').count(),
        },
        'add_form': add_form,
        'edit_form': edit_form,
        'edit_member': None,
        'edit_form_action': '',
        'edit_form_preserve': False,
        'delete_member': None,
        'delete_action': '',
        'delete_preserve': False,
        'open_modal': '',
    }
    context.update(extra)
    return context


def member_list(request):
    return render(request, 'members/member_list.html', _member_context(request))


def member_create(request):
    if request.method == 'POST':
        form = MemberForm(request.POST, prefix='add')
        if form.is_valid():
            member = form.save()
            messages.success(request, f'{member.full_name} was added as a member.')
            return redirect('member_list')
        messages.error(request, 'The member was not saved. Please check the highlighted fields.')
        context = _member_context(request, add_form=form, open_modal='memberAddModal')
        return render(request, 'members/member_list.html', context)

    context = _member_context(request, open_modal='memberAddModal')
    return render(request, 'members/member_list.html', context)


def member_update(request, pk):
    member = get_object_or_404(Member, pk=pk)
    action = reverse('member_update', args=[member.pk])

    if request.method == 'POST':
        form = MemberForm(request.POST, instance=member, prefix='edit')
        if form.is_valid():
            member = form.save()
            messages.success(request, f'{member.full_name} was updated.')
            return redirect('member_list')
        messages.error(request, 'The member was not updated. Please check the highlighted fields.')
        context = _member_context(
            request,
            edit_form=form,
            edit_member=member,
            edit_form_action=action,
            edit_form_preserve=True,
            open_modal='memberEditModal',
        )
        return render(request, 'members/member_list.html', context)

    form = MemberForm(instance=member, prefix='edit')
    context = _member_context(
        request,
        edit_form=form,
        edit_member=member,
        edit_form_action=action,
        edit_form_preserve=True,
        open_modal='memberEditModal',
    )
    return render(request, 'members/member_list.html', context)


def member_delete(request, pk):
    member = get_object_or_404(Member, pk=pk)

    if request.method == 'POST':
        name = member.full_name
        try:
            member.delete()
            messages.success(request, f'{name} was removed from the member list.')
        except ProtectedError:
            messages.error(
                request,
                f'{name} cannot be deleted because they have borrowing history. '
                'Set their status to Inactive instead.',
            )
        return redirect('member_list')

    context = _member_context(
        request,
        delete_member=member,
        delete_action=reverse('member_delete', args=[member.pk]),
        delete_preserve=True,
        open_modal='memberDeleteModal',
    )
    return render(request, 'members/member_list.html', context)


def _borrowing_context(request, borrow_form=None, **extra):
    today = timezone.localdate()
    search = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', 'active').strip()
    member_id = request.GET.get('member', '').strip()

    if status_filter not in {'active', 'overdue', 'returned', 'all'}:
        status_filter = 'active'

    if member_id.isdigit():
        member_id = int(member_id)
    else:
        member_id = None

    borrowings = Borrowing.objects.select_related('book', 'member')

    member_obj = None
    if member_id:
        member_obj = Member.objects.filter(pk=member_id).first()
        if member_obj:
            borrowings = borrowings.filter(member=member_obj)

    if search:
        borrowings = borrowings.filter(
            Q(book__title__icontains=search)
            | Q(book__author__icontains=search)
            | Q(member__full_name__icontains=search)
        )

    counts = {
        'all': borrowings.count(),
        'active': borrowings.filter(returned_on__isnull=True).count(),
        'overdue': borrowings.filter(returned_on__isnull=True, due_on__lt=today).count(),
        'returned': borrowings.filter(returned_on__isnull=False).count(),
    }

    if status_filter == 'active':
        borrowings = borrowings.filter(returned_on__isnull=True)
    elif status_filter == 'overdue':
        borrowings = borrowings.filter(returned_on__isnull=True, due_on__lt=today)
    elif status_filter == 'returned':
        borrowings = borrowings.filter(returned_on__isnull=False)

    if borrow_form is None:
        borrow_form = BorrowingForm(prefix='borrow')

    context = {
        'active_section': 'borrowing',
        'borrowings': borrowings,
        'search': search,
        'status_filter': status_filter,
        'counts': counts,
        'member_obj': member_obj,
        'member_id': member_id,
        'today': today,
        'has_filters': bool(search or member_id),
        'library': LibrarySettings.get_solo(),
        'borrow_form': borrow_form,
        'has_active_members': Member.objects.filter(status='Active').exists(),
        'has_available_books': Book.objects.filter(status='Available').exists(),
        'open_modal': '',
    }
    context.update(extra)
    return context


def borrowing_list(request):
    return render(request, 'borrowing/borrowing_list.html', _borrowing_context(request))


def borrowing_create(request):
    if request.method == 'POST':
        form = BorrowingForm(request.POST, prefix='borrow')
        if form.is_valid():
            borrowing = form.save(commit=False)
            with transaction.atomic():
                borrowing.save()
                book = borrowing.book
                book.status = 'Checked Out'
                book.save(update_fields=['status'])

            messages.success(
                request,
                f'"{book.title}" was borrowed by {borrowing.member.full_name}. '
                f'Due on {borrowing.due_on:%b %d, %Y}.',
            )
            return redirect('borrowing_list')
        messages.error(request, 'The borrowing was not saved. Please check the highlighted fields.')
        context = _borrowing_context(
            request,
            borrow_form=form,
            open_modal='borrowingAddModal',
        )
        return render(request, 'borrowing/borrowing_list.html', context)

    context = _borrowing_context(request, open_modal='borrowingAddModal')
    return render(request, 'borrowing/borrowing_list.html', context)


@require_POST
def borrowing_return(request, pk):
    borrowing = get_object_or_404(
        Borrowing.objects.select_related('book', 'member'),
        pk=pk,
    )

    if borrowing.is_returned:
        messages.info(request, 'That borrowing has already been marked as returned.')
        return redirect('borrowing_list')

    returned_on = timezone.localdate()
    days_late = max((returned_on - borrowing.due_on).days, 0)

    with transaction.atomic():
        borrowing.returned_on = returned_on
        borrowing.save(update_fields=['returned_on'])

        book = borrowing.book
        still_out = (
            Borrowing.objects.filter(book=book, returned_on__isnull=True)
            .exclude(pk=borrowing.pk)
            .exists()
        )
        if not still_out and book.status == 'Checked Out':
            book.status = 'Available'
            book.save(update_fields=['status'])

    if days_late:
        messages.warning(
            request,
            f'"{borrowing.book.title}" was returned {days_late} day(s) late.',
        )
    else:
        messages.success(request, f'"{borrowing.book.title}" was returned successfully.')
    return redirect('borrowing_list')


def reports(request):
    today = timezone.localdate()
    month_start = today.replace(day=1)

    status_rows = dict(
        Book.objects.values_list('status').annotate(total=Count('id'))
    )
    status_breakdown = [
        {
            'label': label,
            'total': status_rows.get(value, 0),
            'badge_class': Book.STATUS_BADGE.get(value, 'secondary'),
        }
        for value, label in Book.STATUS_CHOICES
    ]

    genre_breakdown = (
        Book.objects.exclude(genre__isnull=True)
        .exclude(genre='')
        .values('genre')
        .annotate(total=Count('id'))
        .order_by('-total', 'genre')[:8]
    )

    top_books = (
        Book.objects.annotate(borrow_count=Count('borrowings'))
        .filter(borrow_count__gt=0)
        .order_by('-borrow_count', 'title')[:5]
    )

    overdue_borrowings = (
        Borrowing.objects.select_related('book', 'member')
        .filter(returned_on__isnull=True, due_on__lt=today)
        .order_by('due_on')[:10]
    )

    member_activity = (
        Member.objects.annotate(
            active_count=Count('borrowings', filter=Q(borrowings__returned_on__isnull=True)),
            total_count=Count('borrowings'),
        )
        .order_by('-active_count', '-total_count', 'full_name')[:8]
    )

    stats = {
        'books': Book.objects.count(),
        'members': Member.objects.count(),
        'borrowings': Borrowing.objects.count(),
        'active_borrowings': Borrowing.objects.filter(returned_on__isnull=True).count(),
        'overdue': Borrowing.objects.filter(returned_on__isnull=True, due_on__lt=today).count(),
        'returned': Borrowing.objects.filter(returned_on__isnull=False).count(),
        'this_month': Borrowing.objects.filter(borrowed_on__gte=month_start).count(),
    }

    context = {
        'active_section': 'reports',
        'stats': stats,
        'status_breakdown': status_breakdown,
        'genre_breakdown': genre_breakdown,
        'top_books': top_books,
        'overdue_borrowings': overdue_borrowings,
        'member_activity': member_activity,
        'today': today,
    }
    return render(request, 'reports/reports.html', context)


def library_settings(request):
    library = LibrarySettings.get_solo()

    if request.method == 'POST':
        form = LibrarySettingsForm(request.POST, instance=library)
        if form.is_valid():
            form.save()
            messages.success(request, 'Library settings were saved.')
            return redirect('library_settings')
        messages.error(request, 'Settings were not saved. Please check the highlighted fields.')
    else:
        form = LibrarySettingsForm(instance=library)

    context = {
        'active_section': 'settings',
        'form': form,
        'library': library,
    }
    return render(request, 'library_settings/settings.html', context)
