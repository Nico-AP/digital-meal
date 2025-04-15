import uuid
import secrets
import string

from ddm.datadonation.models import DataDonation
from ddm.participation.models import Participant
from ddm.projects.models import DonationProject
from django_ckeditor_5.fields import CKEditor5Field

from datetime import timedelta
from django.contrib.auth.models import AbstractUser
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


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
    AG = 'AG', _('Aargau')
    AR = 'AR', _('Appenzell Ausserrhoden')
    AI = 'AI', _('Appenzell Innerrhoden')
    BL = 'BL', _('Basel-Landschaft')
    BS = 'BS', _('Basel-Stadt')
    BE = 'BE', _('Bern')
    FR = 'FR', _('Freiburg')
    GE = 'GE', _('Genf')
    GL = 'GL', _('Glarus')
    GR = 'GR', _('Graubünden')
    JU = 'JU', _('Jura')
    LU = 'LU', _('Luzern')
    NE = 'NE', _('Neuenburg')
    NW = 'NW', _('Nidwalden')
    OW = 'OW', _('Obwalden')
    SH = 'SH', _('Schaffhausen')
    SZ = 'SZ', _('Schwyz')
    SO = 'SO', _('Solothurn')
    SG = 'SG', _('St. Gallen')
    TI = 'TI', _('Tessin')
    TG = 'TG', _('Thurgau')
    UR = 'UR', _('Uri')
    VD = 'VD', _('Waadt')
    VS = 'VS', _('Wallis')
    ZG = 'ZG', _('Zug')
    ZH = 'ZH', _('Zürich')


class SchoolLevels(models.TextChoices):
    PRIMARY = 'primary', _('Primarstufe')
    SECONDARY = 'secondary', _('Sekundarstufe I (z.B. Sekundar- oder Realschule, Bezirksschule oder Untergymnasium)')
    GYMNASIUM = 'gymnasium', _('Gymnasiale Maturitätsschulen')
    SPECIALISED_SECONDARY = 'specialised sec.', _('Fachmittelschulen')
    VOCATIONAL = 'vocational', _('Berufsschulen und Berufsmaturitätsschulen')
    PEDAGOGICAL = 'pedagogical', _('Pädagogische Hochschulen')
    SPECIALISED_TERTIARY = 'specialised tert.', _('Fachhochschulen und Höhere Fachhochschulen')
    UNIVERSITY = 'university', _('Universitäre Hochschulen')
    OTHER = 'other', _('Andere')


class InstructionFormats(models.TextChoices):
    REGULAR = 'regular', _('Regulärer Unterricht')
    OPTIONAL = 'optional', _('Wahlpflichtfach, Freifach, Kurs, o.ä.')
    SPECIAL = 'special', _('Sonderwoche o.ä.')


class SchoolSubjects(models.TextChoices):
    LANGUAGE = 'languages', _('Sprachunterricht (Deutsch, Französisch, Englisch, etc.)')
    INFORMATICS = 'informatics and media', _('Medien- und Informatikunterricht, Medienerziehung o.ä.')
    ETHICS = 'ethics, religion', _('"Ethik, Religion, Gemeinschaft" (ERG), Ethikunterricht oder Gesellschaftskunde')
    GENERAL = 'general education', _('"Allgemeinbildender Unterricht" (ABU), o.ä.')
    MATH_TECHNICAL = 'math, nature and technics', _('Mathematik oder "Natur und Technik"')
    SOCIETY = 'society, history, geography', _('"Räume, Zeiten, Gesellschaften" (RZG), Geschichte, Geografie, o.ä.')
    OTHER = 'other', _('Anderes')


class Teacher(models.Model):
    user = models.OneToOneField('tool.User', on_delete=models.CASCADE)
    date_created = models.DateTimeField(auto_now_add=True, null=False)
    name = models.CharField(max_length=50, null=False)
    first_name = models.CharField(max_length=50, null=False)
    canton = models.CharField(
        max_length=2, null=False,
        choices=SwissCantons.choices, verbose_name=_('Kanton'))
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
    base_module = models.ForeignKey(
        'tool.BaseModule',
        on_delete=models.CASCADE,
        verbose_name='Base Module',
        null=True
    )

    sub_modules = models.ManyToManyField('tool.SubModule', blank=True)

    school_level = models.CharField(
        max_length=20,
        null=False,
        choices=SchoolLevels.choices,
        verbose_name=_('Schulstufe')
    )
    school_year = models.IntegerField(
        null=False,
        blank=False,
        validators=[MinValueValidator(1), MaxValueValidator(20)],
        verbose_name=_('Schuljahr')
    )
    subject = models.CharField(
        max_length=100,
        null=False,
        blank=False,
        choices=SchoolSubjects.choices,
        verbose_name=_('Unterrichtsfach')
    )
    instruction_format = models.CharField(
        max_length=20,
        null=False,
        blank=False,
        choices=InstructionFormats.choices,
        verbose_name=_('Unterrichtsformat')
    )
    agb_agree = models.BooleanField(
        null=False,
        blank=False,
        default=False,
        verbose_name=_('AGBs akzeptiert')
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

    def get_related_donation_project(self):
        """Returns Donation Project if it exists, None otherwise."""
        project_id = self.base_module.ddm_project_id
        return DonationProject.objects.filter(url_id=project_id).first()

    def get_classroom_participants(self):
        project = self.get_related_donation_project()
        return Participant.objects.filter(
            project=project, extra_data__url_param__class=self.url_id)

    def get_donation_dates(self):
        """
        Get list of donation dates for current classroom.
        """
        project = self.get_related_donation_project()
        dates = DataDonation.objects.filter(
            project=project,
            participant__extra_data__url_param__class=self.url_id
        ).values_list('time_submitted', flat=True)
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

            self.report_ref_end_date = end_date
            self.save()

        start_date = self.report_ref_end_date.replace(day=1)
        return start_date, self.report_ref_end_date


class BaseModule(models.Model):
    """
    A Base Module corresponds to a 'teaching path'.
    """
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    name = models.CharField(
        max_length=50,
        blank=False,
        null=False
    )
    date_created = models.DateTimeField(
        auto_now_add=True,
        null=False
    )
    active = models.BooleanField(default=False)

    materials_text = CKEditor5Field()

    ddm_path = models.URLField()
    ddm_project_id = models.CharField(max_length=255)  # external ID

    def __str__(self):
        return self.name

    def get_active_sub_modules(self):
        return self.submodule_set.filter(active=True)


class SubModule(models.Model):
    base_module = models.ForeignKey(
        'tool.BaseModule', on_delete=models.SET_NULL, null=True)

    name = models.CharField(max_length=50, blank=False, null=False)
    url_parameter = models.SlugField(max_length=5, blank=False, null=False)
    description = models.TextField()
    materials_text = CKEditor5Field()

    active = models.BooleanField(default=False)

    def __str__(self):
        return self.name
