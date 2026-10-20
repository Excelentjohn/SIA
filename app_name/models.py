from django.db import models
from django.contrib.auth.models import User


class LostFound(models.Model):

    STATUS_CHOICES = [('Lost', 'Lost'), ('Found', 'Found'), ('Claimed', 'Claimed'), ('Pending', 'Pending')]

    item_name = models.CharField(max_length=100)
    description = models.TextField()
    category = models.CharField(max_length=100)
    location = models.CharField(max_length=200)
    date = models.DateField()
    date_found = models.DateField(null=True, blank=True)
    found_by = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    owner_name = models.CharField(max_length=100)

    def __str__(self):
        return self.item_name


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    def __str__(self): return self.name


class Location(models.Model):
    name = models.CharField(max_length=200, unique=True)
    def __str__(self): return self.name


class ArchiveProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='archive_profile')
    photo = models.FileField(upload_to='profile_photos/', blank=True)
    bio = models.CharField(max_length=240, blank=True)

    def __str__(self):
        return f'{self.user.username} profile'
