from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

class SignUpForm(UserCreationForm):
    display_name = forms.CharField(max_length=100, required=True, label='Nome de Exibição', help_text='Como você quer ser chamado?')
    email = forms.EmailField(required=True, label='E-mail')

    class Meta:
        model = User
        fields = ('username', 'email', 'display_name')

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
            user.userprofile.display_name = self.cleaned_data['display_name']
            user.userprofile.save()
        return user
