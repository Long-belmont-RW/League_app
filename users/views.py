from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import UserProfile, User
from league.models import Coach, Player

from .forms import UserRegistrationForm, EmailAuthenticationForm

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
        form = UserRegistrationForm(request.POST, request=request)  # Pass request to the form
        # Check if the form is valid    
        if form.is_valid():
            user = form.save()
            login(request, user, backend='users.authentication.EmailRoleAuthBackend')  # login after registration
            messages.success(request, f"Account created for {user.username}!")
            return redirect('home')  
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = UserRegistrationForm(request=request)  # Pass request to the form
    


    return render(request, 'registration/register.html', {'form': form})

@login_required
def admin_dashboard_view(request):
    all_users = User.objects.all()[:10]
    all_coaches = Coach.objects.all()[:10]
    all_players = Player.objects.all()[:10]
    

    # Check if the user is an admin
    # Redirect if not an admin
    if request.user.role != 'admin':
        messages.error(request, "Only admins can access this page.")
        return redirect('login')
    
    profile = UserProfile.objects.filter(user=request.user)
    context = {
        'profile': profile,
        'all_users': all_users,
        'all_coaches': all_coaches,
        'all_players': all_players,
    }

    return render(request, 'admin_dashboard.html', context)


@login_required
def coach_dashboard_view(request):
    # if request.user.role != 'coach':
    #     messages.error(request, "Only coaches can access this page.")
    #     return redirect('login')
    return render(request, 'coach_dashboard.html')


@login_required
def player_dashboard_view(request):
    # if request.user.role != 'player':
    #     messages.error(request, "Only players can access this page.")
    #     return redirect('login')
    return render(request, 'player_dashboard.html')


@login_required
def fan_dashboard_view(request):
    # if request.user.role != 'fan':
    #     messages.error(request, "Only fans can access this page.")
    #     return redirect('login')
    return render(request, 'fan_dashboard.html')


""""Future improvements:"""
# - Add email verification for new registrations
# - Implement password reset functionality
# - Add user profile management

"""# - Create a custom user creation form for admins to create users"""
# @login_required
# def create_user_view(request):
#     form = CustomUserCreationForm(request.POST or None, request=request)
#     if request.method == 'POST' and form.is_valid():
#         user = form.save(commit=False)
#         user.set_password(form.cleaned_data['password'])
#         user.save()
#         return redirect('user_list')  # or wherever you want
#     return render(request, 'accounts/create_user.html', {'form': form})