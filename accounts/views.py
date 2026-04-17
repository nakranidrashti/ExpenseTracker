
#Username: django-admin
#Email address: dadmin@gmail.com
#Password: dadmin123





from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
import random, string



from accounts.models import Profile

# Create your views here.

    
def register_view(request):

    if request.method == "POST":

        username = request.POST.get("username")
        first_name = request.POST.get("first_name")
        last_name = request.POST.get("last_name")
        email = request.POST.get("email")
        password = request.POST.get("password")
        confirm_password = request.POST.get("confirm_password")
        dob = request.POST.get("dob")

        context = {
            "username": username,
            "first_name": first_name,
            "last_name": last_name,
            "email": email,
            "dob": dob
        }

        # Empty fields validation
        if not username or not email or not password:
            messages.error(request, "All fields are required.")
            return render(request, "register.html", context)

        # Password mismatch
        if password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return render(request, "register.html", context)

        # Username exists
        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists.")
            return render(request, "register.html", context)

        # Email exists
        if User.objects.filter(email=email).exists():
            messages.error(request, "Email already registered.")
            return render(request, "register.html", context)

        # Create user
        User.objects.create_user(
            username=username,
            first_name=first_name,
            last_name=last_name,
            email=email,
            password=password
        )

        messages.success(request, "Account created successfully.")
        return redirect("login")

    return render(request, "register.html")





def login_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        user_captcha = request.POST.get("captcha_input")

        # Verify captcha server-side
        if user_captcha != request.session.get("captcha_text"):
            messages.error(request, "Invalid captcha!")
            return redirect("login")

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect("dashboard")
        else:
            messages.error(request, "Invalid username or password.")
            return redirect("login")

    # GET request: generate new captcha
    captcha_text = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
    request.session["captcha_text"] = captcha_text
    return render(request, "login.html", {"captcha_text": captcha_text})


def logout_view(request):
    logout(request)
    return redirect("index")



@login_required
def profile_view(request):

    user = request.user
    profile = user.profile

    if request.method == "POST":

        user.first_name = request.POST.get("first_name")
        user.last_name = request.POST.get("last_name")
        user.email = request.POST.get("email")

        profile.dob = request.POST.get("dob")
        profile.phone = request.POST.get("phone")
        profile.bio = request.POST.get("bio")

        # upload new photo
        if request.FILES.get("profile_pic"):
            profile.profile_pic = request.FILES.get("profile_pic")

        # remove photo
        if request.POST.get("remove_photo") == "1":

            if profile.profile_pic:
                profile.profile_pic.delete(save=False)

            profile.profile_pic = None

        user.save()
        profile.save()

        messages.success(request,"Profile updated successfully")

        return redirect("profile")

    return render(request,"profile.html")



def forgot_password(request):
    if request.method == "POST":
        username = request.POST.get("username")
        new_password = request.POST.get("new_password")

        try:
            user = User.objects.get(username=username)
            user.set_password(new_password)
            user.save()

            messages.success(request, "Password changed successfully. Please login.")
            return redirect("login")

        except User.DoesNotExist:
            messages.error(request, "Username not found")

    return render(request, "forgot_password.html")