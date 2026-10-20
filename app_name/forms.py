from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import UploadedFile
from .models import LostFound, Category, Location, ArchiveProfile

class UsernameOrEmailAuthenticationForm(AuthenticationForm):
    def clean(self):
        username = self.cleaned_data.get('username')
        if username and '@' in username and not User.objects.filter(username__iexact=username).exists():
            try: self.cleaned_data['username'] = User.objects.get(email__iexact=username).get_username()
            except User.DoesNotExist: pass
            except User.MultipleObjectsReturned: self.cleaned_data['username'] = User.objects.filter(email__iexact=username).order_by('pk').first().get_username()
        return super().clean()

class ItemForm(forms.ModelForm):
    class Meta:
        model = LostFound
        fields = ['item_name', 'description', 'category', 'location', 'date', 'status', 'owner_name']
        widgets = {'date': forms.DateInput(attrs={'type': 'date'}), 'description': forms.Textarea(attrs={'rows': 4})}
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Existing records change status only through the validated case actions.
        if self.instance and self.instance.pk:
            self.fields['status'].disabled = True
        else:
            self.fields['status'].choices = [choice for choice in self.fields['status'].choices if choice[0] != 'Claimed']

    def clean_status(self):
        status = self.cleaned_data['status']
        if not self.instance.pk and status == 'Claimed':
            raise forms.ValidationError('A new record cannot start as claimed. Mark it claimed after recovery.')
        return status
    def clean_category(self): return self.cleaned_data['category'].strip()
    def clean_location(self): return self.cleaned_data['location'].strip()

class CategoryForm(forms.ModelForm):
    class Meta: model = Category; fields = ['name']
    def clean_name(self):
        name = self.cleaned_data['name'].strip()
        if Category.objects.filter(name__iexact=name).exclude(pk=self.instance.pk).exists(): raise forms.ValidationError('A category with this name already exists.')
        return name

class LocationForm(forms.ModelForm):
    class Meta: model = Location; fields = ['name']
    def clean_name(self):
        name = self.cleaned_data['name'].strip()
        if Location.objects.filter(name__iexact=name).exclude(pk=self.instance.pk).exists(): raise forms.ValidationError('A location with this name already exists.')
        return name

class RegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    class Meta: model = User; fields = ('username', 'email', 'password1', 'password2')

class ProfileForm(forms.ModelForm):
    class Meta: model = User; fields = ('first_name', 'last_name', 'email')

class ArchiveProfileForm(forms.ModelForm):
    class Meta:
        model = ArchiveProfile
        fields = ('photo', 'bio')
        widgets = {'photo': forms.FileInput(attrs={'accept': '.jpg,.jpeg,.png,.webp'}), 'bio': forms.Textarea(attrs={'rows': 3, 'maxlength': 240})}

    def clean_photo(self):
        photo = self.cleaned_data.get('photo')
        if not isinstance(photo, UploadedFile):
            return photo
        if photo.size > 5 * 1024 * 1024:
            raise ValidationError('Profile photos must be 5 MB or smaller.')
        extension = photo.name.rsplit('.', 1)[-1].lower() if '.' in photo.name else ''
        header = photo.read(12)
        photo.seek(0)
        valid = ((extension in {'jpg', 'jpeg'} and header.startswith(b'\xff\xd8\xff')) or
                 (extension == 'png' and header.startswith(b'\x89PNG\r\n\x1a\n')) or
                 (extension == 'webp' and header[:4] == b'RIFF' and header[8:12] == b'WEBP'))
        if not valid:
            raise ValidationError('Choose a valid JPG, PNG, or WebP image.')
        return photo
