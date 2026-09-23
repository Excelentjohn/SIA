from django.shortcuts import render
from .models import LostFound # Import your Item model
# Create your views here.
def LostFound(request):
    items = LostFound.objects.all()  # Assuming you have a LostFound model
    context= {
        'LostFound': items
    }
    return render(request, 'InvApp/dashboard.html', context)
