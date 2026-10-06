from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import reverse

from .models import LostFound as LostFoundItem


def dashboard(request):
    queryset = LostFoundItem.objects.all().order_by('-date')
    search_query = (request.GET.get('search') or '').strip()
    status_filter = (request.GET.get('status') or 'all').strip().lower()
    category_filter = (request.GET.get('category') or 'all').strip().lower()
    location_filter = (request.GET.get('location') or 'all').strip().lower()

    if search_query:
        queryset = queryset.filter(
            item_name__icontains=search_query
        ) | queryset.filter(
            description__icontains=search_query
        ) | queryset.filter(
            owner_name__icontains=search_query
        )
        queryset = queryset.distinct()

    if status_filter and status_filter != 'all':
        queryset = queryset.filter(status__iexact=status_filter.title())

    if category_filter and category_filter != 'all':
        queryset = queryset.filter(category__iexact=category_filter.title())

    if location_filter and location_filter != 'all':
        queryset = queryset.filter(location__icontains=location_filter.title())

    total_items = LostFoundItem.objects.count()
    lost_items = LostFoundItem.objects.filter(status__iexact='Lost').count()
    found_items = LostFoundItem.objects.filter(status__iexact='Found').count()
    active_cases = LostFoundItem.objects.filter(status__in=['Lost', 'Pending']).count()

    categories = sorted({item.category for item in LostFoundItem.objects.all() if item.category})
    locations = sorted({item.location for item in LostFoundItem.objects.all() if item.location})

    context = {
        'items': queryset,
        'search_query': search_query,
        'status_filter': status_filter,
        'category_filter': category_filter,
        'location_filter': location_filter,
        'total_items': total_items,
        'lost_items': lost_items,
        'found_items': found_items,
        'active_cases': active_cases,
        'categories': categories,
        'locations': locations,
    }
    return render(request, 'InvApp/dashboard.html', context)


def save_case(request, pk=None):
    if request.method != 'POST':
        return HttpResponseRedirect(reverse('dashboard'))

    item_name = (request.POST.get('item_name') or '').strip()
    description = (request.POST.get('description') or '').strip()
    category = (request.POST.get('category') or '').strip()
    location = (request.POST.get('location') or '').strip()
    date_value = request.POST.get('date')
    status = (request.POST.get('status') or 'Pending').strip()
    owner_name = (request.POST.get('owner_name') or '').strip()

    if not item_name:
        return HttpResponseRedirect(reverse('dashboard'))

    if pk:
        item = get_object_or_404(LostFoundItem, pk=pk)
        item.item_name = item_name
        item.description = description
        item.category = category
        item.location = location
        item.date = date_value or item.date
        item.status = status
        item.owner_name = owner_name
        item.save()
    else:
        LostFoundItem.objects.create(
            item_name=item_name,
            description=description,
            category=category,
            location=location,
            date=date_value,
            status=status,
            owner_name=owner_name,
        )

    return HttpResponseRedirect(reverse('dashboard'))


def case_detail(request, pk):
    item = get_object_or_404(LostFoundItem, pk=pk)
    return render(request, 'InvApp/case_detail.html', {'item': item})


def delete_case(request, pk):
    if request.method == 'POST':
        item = get_object_or_404(LostFoundItem, pk=pk)
        item.delete()
    return HttpResponseRedirect(reverse('dashboard'))


def LostFound(request):
    return dashboard(request)

