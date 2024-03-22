from allauth.account.forms import SignupForm
from django import forms

from .models import SwissCantons, Teacher, Classroom


cantons = SwissCantons.choices
cantons.insert(0, ('', 'bitte auswählen'))


class SimpleSignupForm(SignupForm):
    name = forms.CharField(
        max_length=50,
        label='Nachname',
        widget=forms.TextInput(
            attrs={'placeholder': 'Ihr Nachname'}
        )
    )
    first_name = forms.CharField(
        max_length=50,
        label='Vorname',
        widget=forms.TextInput(
            attrs={'placeholder': 'Ihr Vorname'}
        )
    )
    canton = forms.ChoiceField(
        choices=cantons,
        label='Kanton',
        help_text='Kanton, in dem Sie hauptsächlich unterrichten'
    )
    school_name = forms.CharField(
        max_length=100,
        label='Schule',
        widget=forms.TextInput(
            attrs={'placeholder': 'Name der Schule, an der Sie unterrichten'}
        )
    )

    field_order = [
        'first_name',
        'name',
        'canton',
        'school_name',
        'email',
        'email2',
        'password1',
        'password2',
    ]

    def save(self, request):
        user = super().save(request)
        if not user:
            return None

        form_input = SimpleSignupForm(request.POST)
        if form_input.is_valid():
            Teacher.objects.create(
                user=user,
                name=form_input.cleaned_data['name'],
                first_name=form_input.cleaned_data['first_name'],
                canton=form_input.cleaned_data['canton'],
                school_name=form_input.cleaned_data['school_name']
            )
            user.save()
        return user


class ClassroomCreateForm(forms.ModelForm):
    class Meta:
        model = Classroom
        fields = [
            'name', 'school_level', 'school_year', 'subject',
            'instruction_format', 'agb_agree'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'Name/Bezeichnung der Klasse'}),
            'track': forms.Select(attrs={'style': 'width: 40%; min-width: 300px;'}),
            'school_level': forms.Select(attrs={'style': 'width: 40%; min-width: 300px;'}),
            'subject': forms.Select(attrs={'style': 'width: 40%; min-width: 300px;'}),
            'instruction_format': forms.Select(attrs={'style': 'width: 40%; min-width: 300px;'}),
        }
        labels = {
            'school_level': 'Zu welcher Schulstufe gehört die Klasse?',
            'school_year': 'In welchem Schuljahr befindet sich die Klasse aktuell?',
            'subject': 'In welchem Fachbereich nutzen Sie das Lernmodul mit Ihrer Klasse?',
            'instruction_format': 'In welchem Format unterrichten Sie die Klasse?'
        }
        # TODO: Optimize help text and add link.
        help_texts = {
            'agb_agree': 'Ich bin damit einverstanden, dass ich dieses Modul nur mit Schüler:innen verwende, '
                         'die mindestens 14 Jahre alt sind. Zudem bestätige ich, dass ich die Datenschutzbestimmungen '
                         '<LINK WIRD ERGÄNZT> gelesen habe und damit einverstanden bin.'
        }

    def clean(self):
        cleaned_data = super().clean()
        agb_agreed = cleaned_data.get('agb_agree')
        if not agb_agreed:
            self.add_error(
                'agb_agree',
                'Sie müssen bestätigen, dass Sie die Nutzungsbedingungen '
                'gelesen haben und mit ihnen einverstanden sind.'
            )


class ClassroomTrackForm(forms.ModelForm):
    class Meta:
        model = Classroom
        fields = [
            'track'
        ]
