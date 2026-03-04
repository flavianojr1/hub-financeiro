from django import forms
from django.contrib.auth.models import User
from .models import UserProfile

class ProfileUpdateForm(forms.ModelForm):
    email = forms.EmailField(required=True, label='E-mail')
    display_name = forms.CharField(max_length=100, required=False, label='Nome de Exibição')

    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email')
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and hasattr(self.instance, 'userprofile'):
            self.fields['display_name'].initial = self.instance.userprofile.display_name

    def save(self, commit=True):
        user = super().save(commit=False)
        if commit:
            user.save()
            profile, created = UserProfile.objects.get_or_create(user=user)
            profile.display_name = self.cleaned_data['display_name']
            profile.save()
        return user
