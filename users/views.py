from django.shortcuts import render

from django.contrib.auth import login, authenticate
from django.contrib import messages

from .forms import UserRegistriationForm, EmailAuthenticationForm

#login view
def login_view(request):
    if request.method == 'POST':
        form = EmailAuthenticationForm(request, data=request.POST)

        if form.is_valid():
            email = form.cleaned_data.get('username') #username field contains email
            password = form.cleaned_data.get('password')

            user = authenticate(username=email, password=password)

            if user is not None:
                login (request, user)
            
        else: 
            messages.error(request, "invalid email or password")
    
    form = EmailAuthenticationForm()
    return render(request, 'registration/login.html', {'form':form})