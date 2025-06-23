import uuid
import secrets
import string

from ddm.datadonation.models import DataDonation
from ddm.participation.models import Participant
from ddm.projects.models import DonationProject
from django.db.models import Max
from django_ckeditor_5.fields import CKEditor5Field

from datetime import timedelta, datetime
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
        max_length=2,
        null=False,
        choices=SwissCantons.choices,
        verbose_name=_('Kanton')
    )
    school_name = models.CharField(max_length=100, null=True, blank=True)

    class Meta:
         verbose_name = 'Teacher'

    def __str__(self):
        return f'{self.first_name} {self.name}'


def now_plus_six_months():
    return timezone.now() + timedelta(days=180)


class Classroom(models.Model):
    """
    A Classroom ties participations belonging to one class together (i.e., they
    can be linked with the Classroom.class_id).

    A Classroom always belongs to a specific BaseModule (i.e., a class is
    focused on one BaseModule).

    Attributes:
        owner (tool.User): The user that has created the Classroom.
        name (str): The name of the Classroom as given by the owner on creation.

        url_id (str): A random 10-digit string used as class id in urls and to
            connect participants with ddm (by passing the url_id as url
            parameter to the DonationProject).

        date_created (datetime): Date when the Classroom was created.
        expiry_date (datetime): Date until when the Classroom is accessible
            (i.e., until when the related reports are accessible).

        base_module (BaseModule): The BaseModul for which this Classroom was created.
        sub_modules (SubModule): The SubModules selected for this Classroom.

        school_level (str): The school level of the class with which this
            Classroom is used.
        school_year (int): The school year of the class with which this
            Classroom is used.
        subject (str): The subject of the class with which this
            Classroom is used.
        instruction_format (str): The instruction format of the class with which this
            Classroom is used.

        agb_agree (bool): Whether the AGBs have been accepted by the user on
            creation of the Classroom (should always be True as the creation
            should only be possible when this has been selected).
        report_ref_end_date (datetime): The end date of the reference timeframe
            used in parts of the reports (is set after the first donation for
            this class has been received).
        is_test_participation_class (bool): Whether the Classroom is used to
            collect test participations.
    """

    owner = models.ForeignKey('tool.User', on_delete=models.CASCADE)
    name = models.CharField(max_length=100, null=False)
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

    is_test_participation_class = models.BooleanField(
        default=False,
        help_text=(
            'Select if this class is used to collect test participations.'
        )
    )

    class Meta:
         verbose_name = 'Classroom'

    def __str__(self):
        return self.name

    @property
    def is_active(self):
        if self.is_test_participation_class:
            return True

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

    def get_participation_stats(self):
        """
        Computes basic participation statistics for this classroom:
        - 'n_started'
        - 'n_finished'
        - 'completion_rate'
        - 'last_started'
        - 'last_completed'

        Returns:
            dict: Contains participation stats
        """
        if self.base_module is None:
            return {
                'n_started': 0,
                'n_finished': 0,
                'completion_rate': 0,
                'last_started': None,
                'last_completed': None
            }

        participants = self.get_classroom_participants()

        n_started = len(participants)
        n_finished = len(participants.filter(completed=True))
        if n_started and n_started > 0:
            completion_rate = round(n_finished / n_started, 1)
        else:
            completion_rate = 0

        date_stats = participants.aggregate(
            last_started=Max('start_time'),
            last_completed=Max('end_time')
        )
        date_last_started = date_stats['last_started']
        date_last_completed = date_stats['last_completed']

        result = {
            'n_started': n_started,
            'n_finished': n_finished,
            'completion_rate': completion_rate,
            'last_started': date_last_started,
            'last_completed': date_last_completed
        }
        return result

    def get_donation_dates(self) -> list:
        """
        Get list of donation dates for current classroom.

        Returns:
            list: List of donation dates if any donations exist,
                empty list otherwise.
        """

        project = self.get_related_donation_project()
        dates = DataDonation.objects.filter(
            project=project,
            participant__extra_data__url_param__class=self.url_id
        )

        if dates.exists():
            return dates.values_list('time_submitted', flat=True)

        else:
            return []

    @staticmethod
    def get_previous_month(date: datetime) -> (datetime, datetime):
        """
        Get the start and end date of the previous month relative to the given
        date.

        Args:
            date: A datetime object relative to which the start and end date of
                the previous month is calculated.

        Returns:
            (datetime, datetime): The start and end date of the interval.
        """

        if date.month == 1:
            end_date = date.replace(day=31, month=12)
        else:
            end_date = date.replace(day=1) - timedelta(days=1)

        start_date = end_date.replace(day=1)

        return start_date, end_date

    def get_reference_interval(self) -> (datetime, datetime):
        """
        Computes a reference timespan to be used in parts of the usage reports.
        Classroom.report_ref_end_date is used to store the end date of this
        timespan.

        When a classroom is created, its report_ref_end_date is set to None.
        It will only be set, once the classroom report is requested and at least
        one donation has been received for this class.
        The reference end date is then set to span the last full month previous
        to the submission date of the first donation (i.e., when the donation
        was submitted on 4 April 2025, the timespan is set to cover 1 March to
        31 March 2025).

        Returns:
            (datetime, datetime) | (None, None): A tuple containing the start date and the
                end date of the reference timespan ('start_date', 'end_date').
        """
        if self.is_test_participation_class:
            ref_end_date = timezone.now()
            return self.get_previous_month(ref_end_date)

        if self.report_ref_end_date:
            start_date = self.report_ref_end_date.replace(day=1)
            return start_date, self.report_ref_end_date

        donation_dates = self.get_donation_dates()
        if not donation_dates:
            return None, None

        # Get interval dates
        date_min = min(donation_dates)
        start_date, end_date = self.get_previous_month(date_min)

        self.report_ref_end_date = end_date
        self.save()

        return start_date, self.report_ref_end_date


class BaseModule(models.Model):
    """
    A BaseModule corresponds to a 'teaching path' and is usually related to
    one platform of interest. It ties the data donation, teaching materials,
    reports, and submodules together.

    A BaseModule must always be accompanied by a DonationProject created in DDM.

    Attributes:
        id (str): UUID used as the primary key.
        name (str): Name of the Module as displayed in the UI.
        date_created (datetime): Date when module was created (automatically added).
        active (boolean): If a module is active or not (used to show/hide the
            module in the UI).
        materials_text (str): Textfield to list information and link material
            belonging to this module (included in the UI).
        ddm_project_id (str): The public project ID of the linked
            DDM DonationProject (also see internal documentation).
        ddm_path (str): The participation link of the linked
            DDM DonationProject.
        test_class_url_id (str): The public (URL) ID of the
            DigitalMeal.Tool.Classroom that is used to collect the test
            participations for this module (also see internal documentation).
        report_prefix (str): The prefix used in the url path names to link
            reports to this module (also see internal documentation).

    Note:
        The DDM DonationProject is implicitly linked so that the donation project
            could be hosted on another server.
        The test_class (i.e., the Classroom used to collect test participations)
            is implicitly linked, because it must be created after the module
            has been created. Creation could be automated in a future iteration.
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

    ddm_project_id = models.CharField(
        max_length=255,
        verbose_name='DDM project id'
    )  # external ID
    ddm_path = models.URLField(verbose_name='DDM path')

    test_class_url_id = models.CharField(
        max_length=10,
        null=True,
        blank=True,
        help_text=(
            'The url_id of the class that is used to collect the test cases '
            'for this module (needed for the individual report to work in the '
            'test participation).'
        )
    )

    report_prefix = models.SlugField()

    class Meta:
         verbose_name = 'Base Module'

    def __str__(self):
        return self.name

    def get_active_sub_modules(self):
        return self.submodule_set.filter(active=True)


class SubModule(models.Model):
    """
    A SubModule is a thematic extension of a BaseModule. It can be used to
    make further teaching materials accessible and potentially additional DDM
    components.

    Attributes:
        base_module (BaseModule): The parent BaseModule.
        name (str): Name of the Module to be displayed in the UI.
        description (str): A description of the Module to be displayed in the UI.
            materials_text (str): Textfield to list information and link material
            belonging to this module (included in the UI).
        url_parameter (str): A url parameter specific to this module (used to
            append to DDM participation links with 1 indicating module is selected
            and 0 indicating module is not selected).
        active (boolean): If a module is active or not (used to show/hide the
            module in the UI).
    """

    base_module = models.ForeignKey(
        'tool.BaseModule', on_delete=models.SET_NULL, null=True)

    name = models.CharField(max_length=50, blank=False, null=False)
    description = models.TextField()

    materials_text = CKEditor5Field()

    url_parameter = models.SlugField(
        max_length=5,
        blank=False,
        null=False,
        verbose_name='URL parameter'
    )

    active = models.BooleanField(default=False)

    class Meta:
         verbose_name = 'Sub Module'

    def __str__(self):
        return self.name
