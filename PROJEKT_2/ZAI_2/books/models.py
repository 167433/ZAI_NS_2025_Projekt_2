from django.db import models

# Create your models here.
from django.db import models
from django.contrib.auth.models import User


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class Book(models.Model):
    title = models.CharField(max_length=200)
    author = models.CharField(max_length=150)
    published_year = models.IntegerField(null=True, blank=True)
    external_id = models.CharField(max_length=100, blank=True)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="books")
    categories = models.ManyToManyField(Category, blank=True)

    def __str__(self):
        return self.title


class ReadingEntry(models.Model):
    class Status(models.TextChoices):
        TO_READ = "to_read"
        READING = "reading"
        FINISHED = "finished"

    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name="entries")
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=Status.choices)
    rating = models.IntegerField(null=True, blank=True)
    notes = models.TextField(blank=True)