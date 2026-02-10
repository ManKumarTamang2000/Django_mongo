from django.conf import settings
from django.db import models

# Create your models here.

User=settings.AUTH_USER_MODEL

class ChatMessage(models.Model):
    user=models.ForeignKey(User,on_delete=models.CASCADE)
    message=models.TextField()
    response=models.TextField()
    created_at=models.DateTimeField(auto_now_add=True)


    class Meta:
       pass

    def __str__(self):
        return self.message[:50]    
