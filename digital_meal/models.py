import uuid
from datetime import timedelta

from django.contrib.auth.models import AbstractUser
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.urls import reverse
from django.utils import timezone


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
    user = models.OneToOneField('digital_meal.User', on_delete=models.CASCADE)
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
    owner = models.ForeignKey('digital_meal.User', on_delete=models.CASCADE)
    name = models.CharField(max_length=100, null=False)
    pool_id = models.UUIDField(default=uuid.uuid4, editable=False)  # TODO: Rename - Pool is outdated
    date_created = models.DateTimeField(auto_now_add=True, null=False)
    expiry_date = models.DateTimeField(default=now_plus_six_months, null=False)
    track = models.ForeignKey(
        'digital_meal.Track',
        on_delete=models.CASCADE,
        verbose_name='Track',
        null=True
    )

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

    participant_ids = models.JSONField(default=list)  # list

    def __str__(self):
        return self.name

    def is_active(self):
        if self.expiry_date > timezone.now():
            return True
        else:
            return False

    def get_absolute_url(self):
        return reverse('classroom-detail', kwargs={'pk': self.pk})


class Track(models.Model):
    """
    A Track corresponds to a 'teaching path' within a Module
    (e.g., small, medium etc.).
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=50, blank=False, null=False)
    date_created = models.DateTimeField(auto_now_add=True, null=False)
    active = models.BooleanField(default=False)
    # TODO: Add image/icon field

    ddm_path = models.URLField()
    ddm_project_id = models.CharField(max_length=255)
    ddm_api_endpoint = models.URLField()
    ddm_api_token = models.CharField(max_length=40)

    def __str__(self):
        return self.name
