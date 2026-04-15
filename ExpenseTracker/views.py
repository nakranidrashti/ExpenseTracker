from django.http import HttpResponse
from django.shortcuts import render
from django.core.mail import send_mail
from django.shortcuts import render
from django.contrib import messages


#Media files (media/)

#These are uploaded by users at runtime.

#Examples: profile photos, uploaded receipts, documents.

#Stored in media/ folder and you access them via {{ user.profile.photo.url }}.

#Django serves them only in development (via urlpatterns += static(...)).


def index(request):
    return render(request,'index.html')

