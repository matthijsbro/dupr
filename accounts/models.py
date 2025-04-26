from django.db import models

from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    """
    Custom user model that can be assigned content categories for access control.
    """
    categories = models.ManyToManyField(
        'teachings.Category',
        blank=True,
        related_name='users',
        help_text='Categories this user has access to.'
    )

    def __str__(self):
        return self.username
