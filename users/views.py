from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib import messages

from .forms import UserRegistriationForm, EmailAuthenticationForm

# Login view
def login_view(request):
    if request.method == 'POST':
        form = EmailAuthenticationForm(request, data=request.POST)

        if form.is_valid():
            email = form.cleaned_data.get('username')  # username field contains email
            password = form.cleaned_data.get('password')

            user = authenticate(username=email, password=password)

            if user is not None:
                login(request, user)

                # Get the 'next' parameter if it exists
                next_url = request.POST.get('next') or request.GET.get('next')
                if next_url:
                    return redirect(next_url)
                
                # Default redirect after successful login
                return redirect('home')  
            else:
                messages.error(request, "Invalid email or password")
        else: 
            messages.error(request, "Invalid email or password")
    else:
        form = EmailAuthenticationForm()
    
    return render(request, 'registration/login.html', {'form': form})

def logout_view(request):
    logout(request)
    messages.success(request, "You have been logged out successfully.")
    return redirect('login')

def register_view(request):
    if request.method == 'POST':
        form = UserRegistriationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user, backend='users.authentication.EmailMultiRoleAuthBackend')  # login after registration
            messages.success(request, f"Account created for {user.username}!")
            return redirect('home')  
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = UserRegistriationForm()
    
    return render(request, 'registration/register.html', {'form': form})

def dashboard(request):
    return render(request, 'dashboard.html')