from django.db import models


class LostFound(models.Model):

    item_name = models.CharField(max_length=100)
    description = models.TextField()
    category = models.CharField(max_length=100)
    location = models.CharField(max_length=200)
    date = models.DateField()
    status = models.CharField(max_length=20)
    owner_name = models.CharField(max_length=100)

    def __str__(self):
        return self.item_name