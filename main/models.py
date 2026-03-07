from django.db import models

class HomeBanner(models.Model):
    title = models.CharField(max_length=255)
    image = models.ImageField(upload_to='home_banners/')
    destination_url = models.URLField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title
