from django.db import models
from django.contrib.auth.models import User
# Create your models here.



'''
Some example models to demo the dev_db script
'''


class SiteCategory(models.Model):
    name = models.CharField(max_length=255)

    
class Site(models.Model):
    category = models.ForeignKey(SiteCategory, on_delete=models.CASCADE)

    
class Tag(models.Model):
    name = models.CharField(max_length=25)

    
class Item(models.Model):
    site = models.ForeignKey(Site, on_delete=models.CASCADE)
    url = models.TextField()
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    
    tags = models.ManyToManyField(Tag)
    
# these two models are here to test if things break
# when relations go two ways (infinite loops etcs)
    
class Blogger(models.Model):
    name = models.CharField(max_length=255)
    favourite_post = models.ForeignKey('Post', related_name='favourites', on_delete=models.CASCADE)

    
class Post(models.Model):
    blogger = models.ForeignKey(Blogger, on_delete=models.CASCADE)
