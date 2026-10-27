from django.contrib import admin

from .models import Book, Borrowing, LibrarySettings, Member


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'isbn', 'genre', 'status')
    search_fields = ('title', 'author', 'isbn')
    list_filter = ('status', 'genre')


@admin.register(Member)
class MemberAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'email', 'phone', 'status', 'joined_on')
    search_fields = ('full_name', 'email', 'phone')
    list_filter = ('status',)


@admin.register(Borrowing)
class BorrowingAdmin(admin.ModelAdmin):
    list_display = ('book', 'member', 'borrowed_on', 'due_on', 'returned_on')
    search_fields = ('book__title', 'member__full_name')
    list_filter = ('returned_on',)
    date_hierarchy = 'borrowed_on'
    autocomplete_fields = ('book', 'member')


@admin.register(LibrarySettings)
class LibrarySettingsAdmin(admin.ModelAdmin):
    list_display = ('library_name', 'branch', 'loan_period_days', 'max_books_per_member', 'updated_at')

    def has_add_permission(self, request):
        return not LibrarySettings.objects.exists()
