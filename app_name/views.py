from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView
from django.core.files.storage import default_storage
from django.db.models import Q, Count
from django.db import transaction
from django.utils import timezone
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views.decorators.http import require_POST
from .forms import ItemForm, CategoryForm, LocationForm, RegistrationForm, ProfileForm, ArchiveProfileForm, UsernameOrEmailAuthenticationForm
from .models import LostFound, Category, Location, ArchiveProfile

def sync_directory_values(item):
    if item.category.strip(): Category.objects.get_or_create(name__iexact=item.category.strip(), defaults={'name': item.category.strip()})
    if item.location.strip(): Location.objects.get_or_create(name__iexact=item.location.strip(), defaults={'name': item.location.strip()})

class ArchiveLoginView(LoginView):
    template_name = 'InvApp/form.html'
    authentication_form = UsernameOrEmailAuthenticationForm
    redirect_authenticated_user = True
    extra_context = {'title': 'Sign in'}

class ArchiveLogoutView(LogoutView):
    next_page = reverse_lazy('login')

def register(request):
    form = RegistrationForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save(); login(request, user); return redirect('dashboard')
    return render(request, 'InvApp/form.html', {'form': form, 'title': 'Create account'})

@login_required
def dashboard(request, section='dashboard'):
    all_items = LostFound.objects.all()
    items = all_items.order_by('-date', '-pk')
    search = request.GET.get('search', '').strip()
    requested_status = request.GET.get('status', '').strip()
    requested_category = request.GET.get('category', '').strip()
    requested_location = request.GET.get('location', '').strip()
    valid_statuses = {value.casefold(): value for value, _label in LostFound.STATUS_CHOICES}
    default_status = {'lost': 'Lost', 'found': 'Found'}.get(section, '')
    status = valid_statuses.get(requested_status.casefold(), '') if requested_status and requested_status.casefold() != 'all' else ('' if requested_status else default_status)
    category_rows = list(Category.objects.order_by('name').values_list('name', flat=True))
    item_category_rows = list(all_items.exclude(category='').order_by('category').values_list('category', flat=True).distinct())
    location_rows = list(Location.objects.order_by('name').values_list('name', flat=True))
    item_location_rows = list(all_items.exclude(location='').order_by('location').values_list('location', flat=True).distinct())
    category_names = list(category_rows)
    location_names = list(location_rows)
    for value in item_category_rows:
        if value.casefold() not in {name.casefold() for name in category_names}:
            category_names.append(value)
    for value in item_location_rows:
        if value.casefold() not in {name.casefold() for name in location_names}:
            location_names.append(value)
    category = next((name for name in category_names if name.casefold() == requested_category.casefold()), '') if requested_category.casefold() != 'all' else ''
    location = next((name for name in location_names if name.casefold() == requested_location.casefold()), '') if requested_location.casefold() != 'all' else ''
    if search:
        items = items.filter(Q(item_name__icontains=search) | Q(description__icontains=search) | Q(category__icontains=search) | Q(location__icontains=search) | Q(owner_name__icontains=search))
    if status: items = items.filter(status__iexact=status)
    if category: items = items.filter(category__iexact=category)
    if location: items = items.filter(location__iexact=location)
    categories = [{'name': name, 'total': all_items.filter(category__iexact=name).count()} for name in category_names]
    page_heading = {'lost': 'Lost Items', 'found': 'Found Items', 'cases': 'Cases'}.get(section, 'Lost & Found')
    stats = all_items.aggregate(
        total=Count('pk'),
        lost=Count('pk', filter=Q(status__iexact='Lost')),
        found=Count('pk', filter=Q(status__iexact='Found')),
        claimed=Count('pk', filter=Q(status__iexact='Claimed')),
        active=Count('pk', filter=Q(status__iexact='Lost') | Q(status__iexact='Found') | Q(status__iexact='Pending')),
    )
    ctx = {'items': items, 'section': section, 'page_heading': page_heading, 'search_query': search, 'status_filter': status, 'category_filter': category, 'location_filter': location,
           'archive_profile': ArchiveProfile.objects.filter(user=request.user).first(),
           'total_items': stats['total'], 'case_files': stats['total'], 'lost_items': stats['lost'],
           'found_items': stats['found'], 'claimed_items': stats['claimed'], 'active_cases': stats['active'],
           'categories': [{'name': name} for name in category_names], 'locations': [{'name': name} for name in location_names],
           'category_counts': categories[:8],
           'invalid_filter': bool((requested_status and not status) or (requested_category and requested_category.casefold() != 'all' and not category) or (requested_location and requested_location.casefold() != 'all' and not location))}
    return render(request, 'InvApp/dashboard.html', ctx)

@login_required
def item_list(request, kind):
    if kind not in ('lost', 'found'):
        return redirect('dashboard')
    return dashboard(request, section=kind)

@login_required
def case_list(request):
    return dashboard(request, section='cases')

@login_required
def item_create(request):
    preset_status = request.GET.get('status', '') if request.method == 'GET' else ''
    if preset_status not in {'Lost', 'Found', 'Claimed', 'Pending'}: preset_status = ''
    form = ItemForm(request.POST or None, initial={'status': preset_status} if preset_status else None)
    if request.method == 'POST' and form.is_valid():
        item = form.save(commit=False)
        if item.status.casefold() == 'found':
            item.date_found = timezone.localdate()
            item.found_by = request.user.get_full_name().strip() or request.user.get_username()
        item.save(); sync_directory_values(item); messages.success(request, 'Item added successfully.'); return redirect('case_detail', pk=item.pk)
    title = {'Lost': 'Report lost item', 'Found': 'Report found item'}.get(preset_status, 'Add case')
    return render(request, 'InvApp/form.html', {'form': form, 'title': title})

@login_required
@require_POST
def transition_case(request, pk, target):
    transitions = {'Pending': {'Lost', 'Found'}, 'Lost': {'Found'}, 'Found': {'Claimed'}}
    with transaction.atomic():
        item = get_object_or_404(LostFound.objects.select_for_update(), pk=pk)
        allowed = transitions.get(item.status.title(), set())
        if target not in {'Lost', 'Found', 'Claimed'} or target not in allowed:
            messages.error(request, f'Cannot change this record from {item.status} to {target}.')
            return redirect('case_detail', pk=pk)
        item.status = target
        update_fields = ['status']
        if target == 'Found':
            item.date_found = timezone.localdate()
            item.found_by = request.user.get_full_name().strip() or request.user.get_username()
            update_fields.extend(['date_found', 'found_by'])
        item.save(update_fields=update_fields)
    messages.success(request, {'Found': 'Item marked as found. The case remains active until recovery is confirmed.', 'Claimed': 'Recovery confirmed. The case is now resolved.', 'Lost': 'Record marked as lost.'}[target])
    return redirect('case_detail', pk=pk)

@login_required
def item_edit(request, pk):
    item = get_object_or_404(LostFound, pk=pk); form = ItemForm(request.POST or None, instance=item)
    if request.method == 'POST' and form.is_valid():
        item = form.save(); sync_directory_values(item); messages.success(request, 'Item updated successfully.'); return redirect('case_detail', pk=pk)
    return render(request, 'InvApp/form.html', {'form': form, 'title': 'Edit item', 'item': item})

@login_required
def case_detail(request, pk): return render(request, 'InvApp/case_detail.html', {'item': get_object_or_404(LostFound, pk=pk)})

@login_required
@require_POST
def delete_case(request, pk):
    get_object_or_404(LostFound, pk=pk).delete()
    messages.success(request, 'Record deleted.')
    destination = request.POST.get('return_to', '')
    if destination == 'cases': return redirect('cases')
    if destination == 'lost': return redirect('item_list', kind='lost')
    if destination == 'found': return redirect('item_list', kind='found')
    return redirect('dashboard')

@login_required
def directory(request, kind):
    model, form_class = (Category, CategoryForm) if kind == 'categories' else (Location, LocationForm)
    label = 'Category' if kind == 'categories' else 'Location'
    form = form_class(request.POST or None); query = request.GET.get('search', '').strip()
    if request.method == 'POST' and form.is_valid():
        try: form.save(); messages.success(request, f'{label} added.'); return redirect(kind)
        except Exception: form.add_error('name', 'This name already exists.')
    records = model.objects.filter(name__icontains=query).order_by('name')
    return render(request, 'InvApp/directory.html', {'kind': kind, 'records': records, 'form': form, 'search': query, 'archive_profile': ArchiveProfile.objects.filter(user=request.user).first()})

@login_required
def directory_edit(request, kind, pk):
    model, form_class = (Category, CategoryForm) if kind == 'categories' else (Location, LocationForm)
    label = 'Category' if kind == 'categories' else 'Location'
    obj = get_object_or_404(model, pk=pk); form = form_class(request.POST or None, instance=obj)
    if request.method == 'POST' and form.is_valid():
        old_name = obj.name; updated = form.save()
        field = 'category' if kind == 'categories' else 'location'
        LostFound.objects.filter(**{f'{field}__iexact': old_name}).update(**{field: updated.name})
        messages.success(request, 'Updated.'); return redirect(kind)
    return render(request, 'InvApp/form.html', {'form': form, 'title': f'Edit {label.lower()}'})

@login_required
@require_POST
def directory_delete(request, kind, pk):
    model = Category if kind == 'categories' else Location
    obj = get_object_or_404(model, pk=pk)
    used = LostFound.objects.filter(category__iexact=obj.name).exists() if kind == 'categories' else LostFound.objects.filter(location__iexact=obj.name).exists()
    if used: messages.error(request, 'Cannot delete a value that is used by item records.')
    else: obj.delete(); messages.success(request, 'Deleted.')
    return redirect(kind)

@login_required
def reports(request):
    qs = LostFound.objects.all(); start = request.GET.get('from', ''); end = request.GET.get('to', '')
    if start: qs = qs.filter(date__gte=start)
    if end: qs = qs.filter(date__lte=end)
    active = Q(status__iexact='Lost') | Q(status__iexact='Found') | Q(status__iexact='Pending')
    return render(request, 'InvApp/reports.html', {'items': qs, 'total_lost': qs.filter(status__iexact='Lost').count(), 'total_found': qs.filter(status__iexact='Found').count(), 'recovered': qs.filter(status__iexact='Claimed').count(), 'unresolved': qs.filter(active).count(), 'by_category': qs.values('category').annotate(total=Count('id')).order_by('category'), 'by_location': qs.values('location').annotate(total=Count('id')).order_by('location'), 'start': start, 'end': end, 'archive_profile': ArchiveProfile.objects.filter(user=request.user).first()})

@login_required
def profile(request):
    archive_profile, _created = ArchiveProfile.objects.get_or_create(user=request.user)
    user_form = ProfileForm(request.POST or None, instance=request.user, prefix='user')
    archive_form = ArchiveProfileForm(request.POST or None, request.FILES or None, instance=archive_profile, prefix='archive')
    if request.method == 'POST' and user_form.is_valid() and archive_form.is_valid():
        old_photo_name = archive_profile.photo.name if archive_profile.photo else ''
        with transaction.atomic():
            user_form.save()
            archive_profile = archive_form.save()
        if old_photo_name and old_photo_name != archive_profile.photo.name:
            default_storage.delete(old_photo_name)
        messages.success(request, 'Your archive profile has been updated.')
        return redirect('profile')
    items = LostFound.objects.all()
    return render(request, 'InvApp/profile.html', {
        'user_form': user_form, 'archive_form': archive_form, 'archive_profile': archive_profile,
        'total_items': items.count(), 'lost_items': items.filter(status__iexact='Lost').count(),
        'found_items': items.filter(status__iexact='Found').count(),
    })

@login_required
def settings_page(request): return render(request, 'InvApp/settings.html')
