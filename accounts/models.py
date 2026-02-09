from django.db import models
from django.conf import settings


class UserProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='profile',
    )
    points = models.IntegerField(default=0)

    def __str__(self):
        return f'{self.user.username} Profile'

    def deduct_points(self, amount, reason=''):
        self.points -= amount
        self.save(update_fields=['points'])
