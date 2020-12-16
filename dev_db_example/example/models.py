from django.db import models
from django.contrib.auth.models import User

"""
Some example models to test the dev_db script
"""


class UserDependency(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    forward_dependency = models.ForeignKey(
        "ForwardDependency", on_delete=models.CASCADE
    )
    text = models.TextField()


class ForwardDependency(models.Model):
    bool = models.BooleanField()


class ReverseDependency(models.Model):
    dependency = models.ForeignKey(UserDependency, on_delete=models.CASCADE)
    date = models.DateField(auto_now_add=True)
    more_text = models.TextField()


class Loop(models.Model):
    dependency = models.ForeignKey(
        ReverseDependency, on_delete=models.CASCADE, null=True, blank=True
    )
    parent = models.ForeignKey("self", on_delete=models.CASCADE, null=True, blank=True)
    loop_text = models.TextField()


class NotRelatedToUser(models.Model):
    dependency = models.ForeignKey(
        "NotRelatedToUserDependency", on_delete=models.CASCADE
    )
    text = models.TextField()


class NotRelatedToUserDependency(models.Model):
    text = models.TextField()


class M2MRegular(models.Model):
    m2m = models.ManyToManyField(NotRelatedToUser)
    text = models.TextField()


class M2MThrough(models.Model):
    m2m = models.ManyToManyField(NotRelatedToUser, through="Through")
    text = models.TextField()


class Through(models.Model):
    m2m = models.ForeignKey(M2MThrough, on_delete=models.CASCADE)
    not_related = models.ForeignKey(NotRelatedToUser, on_delete=models.CASCADE)
    some_data = models.TextField()


class Extra(models.Model):
    extra_chars = models.CharField(max_length=255)
