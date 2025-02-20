import datetime
import json
import uuid
import requests
import secrets
import string

from django_ckeditor_5.fields import CKEditor5Field

from datetime import timedelta
from django.contrib.auth.models import AbstractUser
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.timezone import make_aware


def generate_unique_classroom_id() -> str:
    """
    Generate a random 10-character URL-safe ID.
    Checks that generated ID is unique for Classrooms.
    """
    allowed_chars = string.ascii_uppercase + string.digits
    while True:
        unique_id = ''.join(secrets.choice(allowed_chars) for _ in range(10))
        if not Classroom.objects.filter(url_id=unique_id).exists():
            return unique_id


class User(AbstractUser):
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['email'], name='unique email')
        ]


class SwissCantons(models.TextChoices):
    AG = 'AG', 'Aargau'
    AR = 'AR', 'Appenzell Ausserrhoden'
    AI = 'AI', 'Appenzell Innerrhoden'
    BL = 'BL', 'Basel-Landschaft'
    BS = 'BS', 'Basel-Stadt'
    BE = 'BE', 'Bern'
    FR = 'FR', 'Freiburg'
    GE = 'GE', 'Genf'
    GL = 'GL', 'Glarus'
    GR = 'GR', 'Graubünden'
    JU = 'JU', 'Jura'
    LU = 'LU', 'Luzern'
    NE = 'NE', 'Neuenburg'
    NW = 'NW', 'Nidwalden'
    OW = 'OW', 'Obwalden'
    SH = 'SH', 'Schaffhausen'
    SZ = 'SZ', 'Schwyz'
    SO = 'SO', 'Solothurn'
    SG = 'SG', 'St. Gallen'
    TI = 'TI', 'Tessin'
    TG = 'TG', 'Thurgau'
    UR = 'UR', 'Uri'
    VD = 'VD', 'Waadt'
    VS = 'VS', 'Wallis'
    ZG = 'ZG', 'Zug'
    ZH = 'ZH', 'Zürich'


class SchoolLevels(models.TextChoices):
    PRIMARY = 'primary', 'Primarstufe'
    SECONDARY = 'secondary', 'Sekundarstufe I (z.B. Sekundar- oder Realschule, Bezirksschule oder Untergymnasium)'
    GYMNASIUM = 'gymnasium', 'Gymnasiale Maturitätsschulen'
    SPECIALISED_SECONDARY = 'specialised sec.', 'Fachmittelschulen'
    VOCATIONAL = 'vocational', 'Berufsschulen und Berufsmaturitätsschulen'
    PEDAGOGICAL = 'pedagogical', 'Pädagogische Hochschulen'
    SPECIALISED_TERTIARY = 'specialised tert.', 'Fachhochschulen und Höhere Fachhochschulen'
    UNIVERSITY = 'university', 'Universitäre Hochschulen'
    OTHER = 'other', 'Andere'


class InstructionFormats(models.TextChoices):
    REGULAR = 'regular', 'Regulärer Unterricht'
    OPTIONAL = 'optional', 'Wahlpflichtfach, Freifach, Kurs, o.ä.'
    SPECIAL = 'special', 'Sonderwoche o.ä.'


class SchoolSubjects(models.TextChoices):
    LANGUAGE = 'languages', 'Sprachunterricht (Deutsch, Französisch, Englisch, etc.)'
    INFORMATICS = 'informatics and media', 'Medien- und Informatikunterricht, Medienerziehung o.ä.'
    ETHICS = 'ethics, religion', '"Ethik, Religion, Gemeinschaft" (ERG), Ethikunterricht oder Gesellschaftskunde'
    GENERAL = 'general education', '"Allgemeinbildender Unterricht" (ABU), o.ä.'
    MATH_TECHNICAL = 'math, nature and technics', 'Mathematik oder "Natur und Technik"'
    SOCIETY = 'society, history, geography', '"Räume, Zeiten, Gesellschaften" (RZG), Geschichte, Geografie, o.ä.'
    OTHER = 'other', 'Anderes'


class Teacher(models.Model):
    user = models.OneToOneField('tool.User', on_delete=models.CASCADE)
    date_created = models.DateTimeField(auto_now_add=True, null=False)
    name = models.CharField(max_length=50, null=False)
    first_name = models.CharField(max_length=50, null=False)
    canton = models.CharField(
        max_length=2, null=False,
        choices=SwissCantons.choices, verbose_name='Kanton')
    school_name = models.CharField(max_length=100, null=True, blank=True)

    def __str__(self):
        return f'{self.first_name} {self.name}'


def now_plus_six_months():
    return timezone.now() + timedelta(days=180)


class Classroom(models.Model):
    owner = models.ForeignKey('tool.User', on_delete=models.CASCADE)
    name = models.CharField(max_length=100, null=False)
    class_id = models.UUIDField(default=uuid.uuid4, editable=False)
    url_id = models.SlugField(
        max_length=10,
        unique=True,
        default=generate_unique_classroom_id,
    )
    date_created = models.DateTimeField(auto_now_add=True, null=False)
    expiry_date = models.DateTimeField(default=now_plus_six_months, null=False)
    track = models.ForeignKey(
        'tool.MainTrack',
        on_delete=models.CASCADE,
        verbose_name='Main Track',
        null=True
    )

    sub_tracks = models.ManyToManyField('tool.SubTrack', blank=True)

    school_level = models.CharField(
        max_length=20,
        null=False,
        choices=SchoolLevels.choices,
        verbose_name='Schulstufe'
    )
    school_year = models.IntegerField(
        null=False,
        blank=False,
        validators=[MinValueValidator(1), MaxValueValidator(20)],
        verbose_name='Schuljahr'
    )
    subject = models.CharField(
        max_length=100,
        null=False,
        blank=False,
        choices=SchoolSubjects.choices,
        verbose_name='Unterrichtsfach'
    )
    instruction_format = models.CharField(
        max_length=20,
        null=False,
        blank=False,
        choices=InstructionFormats.choices,
        verbose_name='Unterrichtsformat'
    )
    agb_agree = models.BooleanField(
        null=False,
        blank=False,
        default=False,
        verbose_name='AGBs akzeptiert'
    )

    report_ref_end_date = models.DateTimeField(null=True, default=None)

    def __str__(self):
        return self.name

    @property
    def is_active(self):
        if self.expiry_date > timezone.now():
            return True
        else:
            return False

    def get_absolute_url(self):
        return reverse('class_detail', kwargs={'url_id': self.url_id})

    def get_donation_dates(self):
        """
        Get list of donation dates for current class through ClassOverviewAPI.
        """
        endpoint = self.track.overview_endpoint
        header = {'Authorization': f'Token {self.track.ddm_api_token}'}
        payload = {'class': self.class_id, }

        r = requests.get(endpoint, headers=header, params=payload)

        if not r.ok:
            return None

        data = json.loads(r.json())
        dates = [datetime.datetime.strptime(d, '%Y-%m-%dT%H:%M:%S.%fZ') for d in data['donation_dates']]
        return dates

    def get_reference_interval(self):
        """
        Computes the date interval of the reference timespan for the usage
        reports.
        Returns a tuple containing the start date and the end date of the
        reference timespan ('start_date', 'end_date').
        """
        if not self.report_ref_end_date:
            donation_dates = self.get_donation_dates()

            # Calculate reference date
            date_min = min(donation_dates)
            if date_min.month == 1:
                end_date = date_min.replace(day=31, month=12)
            else:
                end_date = date_min.replace(day=1) - timedelta(days=1)

            self.report_ref_end_date = make_aware(end_date)
            self.save()

        start_date = self.report_ref_end_date.replace(day=1)
        return start_date, self.report_ref_end_date


class MainTrack(models.Model):
    """
    A Track corresponds to a 'teaching path' within a Module
    (e.g., small, medium etc.).
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=50, blank=False, null=False)
    date_created = models.DateTimeField(auto_now_add=True, null=False)
    active = models.BooleanField(default=False)
    image = models.ImageField(null=True, blank=True, upload_to='uploads/images/%Y/%m/')

    materials_text = CKEditor5Field()

    ddm_path = models.URLField()
    ddm_project_id = models.CharField(max_length=255)  # external ID
    data_endpoint = models.URLField()
    overview_endpoint = models.URLField()
    ddm_api_token = models.CharField(max_length=40)

    def __str__(self):
        return self.name

    def get_active_sub_tracks(self):
        return self.subtrack_set.filter(active=True)


class SubTrack(models.Model):
    """."""
    main_track = models.ForeignKey(
        'tool.MainTrack', on_delete=models.SET_NULL, null=True)

    name = models.CharField(max_length=50, blank=False, null=False)
    url_parameter = models.SlugField(max_length=5, blank=False, null=False)
    description = models.TextField()
    materials_text = CKEditor5Field()

    active = models.BooleanField(default=False)

    def __str__(self):
        return self.name
