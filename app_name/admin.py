from django.contrib import admin

# Register your models here.
from .models import LostFound, Category, Location, ArchiveProfile

admin.site.register(LostFound)
admin.site.register(Category)
admin.site.register(Location)
admin.site.register(ArchiveProfile)
