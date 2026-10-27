document.addEventListener('DOMContentLoaded', function () {
    const sidebar = document.getElementById('appSidebar');
    const toggle = document.querySelector('.sidebar-toggle');
    const backdrop = document.querySelector('.sidebar-backdrop');

    function openSidebar() {
        if (!sidebar) return;
        sidebar.classList.add('show');
        if (backdrop) backdrop.classList.add('show');
        if (toggle) toggle.setAttribute('aria-expanded', 'true');
    }

    function closeSidebar() {
        if (!sidebar) return;
        sidebar.classList.remove('show');
        if (backdrop) backdrop.classList.remove('show');
        if (toggle) toggle.setAttribute('aria-expanded', 'false');
    }

    if (toggle) {
        toggle.addEventListener('click', function () {
            if (sidebar.classList.contains('show')) {
                closeSidebar();
            } else {
                openSidebar();
            }
        });
    }

    if (backdrop) {
        backdrop.addEventListener('click', closeSidebar);
    }

    document.addEventListener('keydown', function (event) {
        if (event.key === 'Escape') {
            closeSidebar();
        }
    });

    if (sidebar) {
        sidebar.querySelectorAll('a.nav-link').forEach(function (link) {
            link.addEventListener('click', closeSidebar);
        });
    }

    function setFormValue(form, name, value) {
        const field = form ? form.querySelector('[name="' + name + '"]') : null;
        if (field) {
            field.value = value || '';
        }
    }

    function setText(scope, selector, value) {
        const element = scope ? scope.querySelector(selector) : null;
        if (element) {
            element.textContent = value || '';
        }
    }

    function bindModalPopulation(modalId, populate) {
        const modalElement = document.getElementById(modalId);
        if (!modalElement) return;

        modalElement.addEventListener('show.bs.modal', function (event) {
            if (modalElement.dataset.preserve === '1') {
                modalElement.dataset.preserve = '0';
                return;
            }

            if (!event.relatedTarget) return;
            populate(modalElement, event.relatedTarget);
        });
    }

    bindModalPopulation('bookEditModal', function (modalElement, trigger) {
        const form = document.getElementById('bookEditForm');
        if (form) form.action = trigger.dataset.action || '';

        setFormValue(form, 'edit-title', trigger.dataset.title);
        setFormValue(form, 'edit-author', trigger.dataset.author);
        setFormValue(form, 'edit-isbn', trigger.dataset.isbn);
        setFormValue(form, 'edit-genre', trigger.dataset.genre);
        setFormValue(form, 'edit-status', trigger.dataset.status);
        setText(modalElement, '[data-edit-title]', trigger.dataset.title || 'this book');
    });

    bindModalPopulation('bookDeleteModal', function (modalElement, trigger) {
        const form = document.getElementById('bookDeleteForm');
        if (form) form.action = trigger.dataset.action || '';

        setText(modalElement, '[data-delete-title]', trigger.dataset.title || 'this book');
    });

    bindModalPopulation('memberEditModal', function (modalElement, trigger) {
        const form = document.getElementById('memberEditForm');
        if (form) form.action = trigger.dataset.action || '';

        setFormValue(form, 'edit-full_name', trigger.dataset.fullName);
        setFormValue(form, 'edit-email', trigger.dataset.email);
        setFormValue(form, 'edit-phone', trigger.dataset.phone);
        setFormValue(form, 'edit-address', trigger.dataset.address);
        setFormValue(form, 'edit-joined_on', trigger.dataset.joinedOn);
        setFormValue(form, 'edit-status', trigger.dataset.status);
        setText(modalElement, '[data-edit-name]', trigger.dataset.fullName || 'this member');
    });

    bindModalPopulation('memberDeleteModal', function (modalElement, trigger) {
        const form = document.getElementById('memberDeleteForm');
        if (form) form.action = trigger.dataset.action || '';

        setText(modalElement, '[data-delete-name]', trigger.dataset.fullName || 'this member');
    });

    bindModalPopulation('returnModal', function (modalElement, trigger) {
        const form = document.getElementById('returnForm');
        if (form) form.action = trigger.dataset.action || '';

        setText(modalElement, '[data-return-book]', trigger.dataset.book || 'this book');
        setText(modalElement, '[data-return-member]', trigger.dataset.member || 'this member');
        setText(modalElement, '[data-return-due]', trigger.dataset.due || '—');
    });

    const autoModal = document.querySelector('[data-auto-modal]');
    if (autoModal && autoModal.dataset.autoModal) {
        const modalElement = document.getElementById(autoModal.dataset.autoModal);
        if (modalElement) {
            bootstrap.Modal.getOrCreateInstance(modalElement).show();
        }
    }
});
