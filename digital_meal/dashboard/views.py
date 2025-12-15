from ddm.apis.serializers import ResponseSerializer
from ddm.datadonation.models import DonationBlueprint
from ddm.logging.models import ExceptionLogEntry
from ddm.participation.models import Participant
from ddm.projects.models import DonationProject
from ddm.questionnaire.models import QuestionnaireResponse
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import UserPassesTestMixin
from django.db.models import Count, Q, Value
from django.db.models.functions import Concat
from django.utils import timezone
from django.views.generic import TemplateView

from digital_meal.tool.models import Classroom, Teacher, BaseModule

User = get_user_model()


class DashboardView(UserPassesTestMixin, TemplateView):
    template_name = 'dashboard/dashboard.html'

    def test_func(self):
        """Requesting user must pass this test to access view."""
        return self.request.user.is_staff


class ClassroomOverviewView(UserPassesTestMixin, TemplateView):
    """HTMX endpoint for loading participant statistics."""
    template_name = 'dashboard/partials/classroom_overview.html'

    def test_func(self):
        """Requesting user must pass this test to access view."""
        return self.request.user.is_staff

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        time_now = timezone.now()

        classrooms = Classroom.objects.exclude(
            Q(is_test_participation_class=True) |
            Q(owner__is_staff=True)
        )

        # Overview
        context['total_classrooms'] = classrooms.count()
        context['active_classrooms'] = classrooms.filter(
            expiry_date__gte=time_now
        ).count()
        context['expired_classrooms'] = classrooms.filter(
            expiry_date__lt=time_now
        ).count()

        # By Module
        context['classrooms_by_module'] = classrooms.values(
            'base_module__name'
        ).annotate(
            count=Count('id'),
            n_active=Count('id', filter=Q(expiry_date__gte=time_now)),
            n_expired=Count('id', filter=Q(expiry_date__lt=time_now)),
        ).order_by('-count')

        # By Submodule
        context['classrooms_by_submodule'] = classrooms.values(
            'sub_modules__pk'
        ).annotate(
            name=Concat('base_module__name', Value(': '), 'sub_modules__name'),
            count=Count('id'),
            n_active=Count('id', filter=Q(expiry_date__gte=time_now)),
            n_expired=Count('id', filter=Q(expiry_date__lt=time_now)),
        ).order_by('-count')

        # By Level
        context['classrooms_by_level'] = classrooms.values(
            'school_level'
        ).annotate(
            count=Count('id'),
            n_active=Count('id', filter=Q(expiry_date__gte=time_now)),
            n_expired=Count('id', filter=Q(expiry_date__lt=time_now)),
        ).order_by('school_level')

        # By Subject
        context['classrooms_by_subject'] = classrooms.values(
            'subject'
        ).annotate(
            count=Count('id'),
            n_active=Count('id', filter=Q(expiry_date__gte=time_now)),
            n_expired=Count('id', filter=Q(expiry_date__lt=time_now)),
        ).order_by('subject')

        # By Instruction Format
        context['classrooms_by_format'] = classrooms.values(
            'instruction_format'
        ).annotate(
            count=Count('id'),
            n_active=Count('id', filter=Q(expiry_date__gte=time_now)),
            n_expired=Count('id', filter=Q(expiry_date__lt=time_now)),
        ).order_by('instruction_format')

        context['recent_classrooms'] = classrooms.select_related(
            'owner', 'owner__teacher', 'base_module'
        ).order_by('-date_created')[:10]

        return context


class TeacherOverviewView(UserPassesTestMixin, TemplateView):
    """HTMX endpoint for loading participant statistics."""
    template_name = 'dashboard/partials/teacher_overview.html'

    def test_func(self):
        """Requesting user must pass this test to access view."""
        return self.request.user.is_staff

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        teacher_users = User.objects.exclude(is_staff=True)
        teachers = Teacher.objects.filter(user__in=teacher_users)

        context['teachers_with_classroom'] = teacher_users.filter(
            classroom__isnull=False
        ).distinct().count()

        context['teachers_without_classroom'] = teacher_users.filter(
            classroom__isnull=True
        ).count()

        context['recent_teachers'] = teacher_users.select_related(
            'teacher'
        ).order_by('-date_joined')[:10]

        context['teachers_by_canton'] = teachers.values(
            'canton'
        ).annotate(count=Count('id')).order_by('-count')[:10]

        return context


class ParticipationOverviewView(UserPassesTestMixin, TemplateView):
    """HTMX endpoint for loading participant statistics."""
    template_name = 'dashboard/partials/participation_overview.html'

    def test_func(self):
        """Requesting user must pass this test to access view."""
        return self.request.user.is_staff

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get relevant classrooms
        classrooms = Classroom.objects.exclude(
            Q(is_test_participation_class=True) |
            Q(owner__is_staff=True)
        ).select_related('base_module').all()

        # Get all base modules with aggregated classroom counts
        base_modules = BaseModule.objects.annotate(
            classroom_count=Count(
                'classroom',
                filter=Q(
                    classroom__is_test_participation_class=False,
                    classroom__owner__is_staff=False
                )
            )
        )

        # Fetch all projects with blueprints in one go
        project_ids = [m.ddm_project_id for m in base_modules if m.ddm_project_id]
        donation_projects = DonationProject.objects.filter(
            url_id__in=project_ids
        ).prefetch_related('donationblueprint_set')

        # Create a project lookup dict
        projects_by_url_id = {p.url_id: p for p in donation_projects}

        info_per_module = {}
        for module in base_modules:
            module_name = module.name

            # Gather base information
            classroom_ids = list(
                classrooms.filter(base_module=module).values_list('url_id', flat=True)
            )
            donation_project = projects_by_url_id.get(module.ddm_project_id)

            if not donation_project:
                continue

            # Single query for all participant stats
            participant_stats = Participant.objects.filter(
                project=donation_project,
                extra_data__url_param__class__in=classroom_ids
            ).aggregate(
                total=Count('id'),
                completed=Count('id', filter=Q(completed=True))
            )

            # Get all participants for relevant classroom
            participants = Participant.objects.filter(
                project=donation_project,
                extra_data__url_param__class__in=classroom_ids
            )

            # Get responses
            responses = QuestionnaireResponse.objects.filter(participant__in=participants)
            response_data = ResponseSerializer(responses, many=True).data

            # Set of participant IDs who consented to the donation
            consented_participant_ids = {
                response['participant']
                for response in response_data
                if response['response_data'].get('usage_dd_consent') in [1, '1']
            }

            # Process blueprints to gather blueprint specific stats
            blueprints_info = {}
            blueprints = donation_project.donationblueprint_set.all()

            for blueprint in blueprints:
                uploaded_donations = blueprint.datadonation_set.filter(
                    participant__in=participants,
                    status='success'
                ).values_list('participant__external_id', flat=True)

                uploaded_participant_ids = set(uploaded_donations)
                n_uploaded = len(uploaded_participant_ids)

                # Check donation consent
                n_agreed_to_donate = len(uploaded_participant_ids & consented_participant_ids)

                donation_rate = (n_agreed_to_donate / n_uploaded) if n_uploaded > 0 else 0

                blueprints_info[blueprint.name] = {
                    'n_uploaded': n_uploaded,
                    'n_donated': n_agreed_to_donate,
                    'donation_rate': donation_rate
                }

            # Get overall participation counts
            n_classrooms = len(classroom_ids)
            n_started = participant_stats['total']
            n_completed = participant_stats['completed']

            info_per_module[module_name] = {
                'id': module.pk,
                'classrooms': n_classrooms,
                'total': n_started,
                'completed': n_completed,
                'completion_rate': (n_completed / n_started * 100) if n_started > 0 else 0,
                'avg_per_classroom': n_started / n_classrooms if n_classrooms > 0 else 0,
                'blueprints': blueprints_info
            }

        # Calculate totals
        total_participants = sum(m['total'] for m in info_per_module.values())
        total_completed = sum(m['completed'] for m in info_per_module.values())
        total_classrooms = classrooms.count()

        context['total_participants'] = total_participants
        context['total_completed'] = total_completed
        context['completion_rate'] = (total_completed / total_participants * 100) if total_participants > 0 else 0
        context['avg_per_classroom'] = total_participants / total_classrooms if total_classrooms > 0 else 0
        context['participants_by_module'] = dict(sorted(info_per_module.items()))

        return context


class ExceptionOverviewView(UserPassesTestMixin, TemplateView):
    """HTMX endpoint for loading exception statistics."""
    template_name = 'dashboard/partials/exception_overview.html'

    def test_func(self):
        """Requesting user must pass this test to access view."""
        return self.request.user.is_staff

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        BLUEPRINT_EXCEPTIONS = [
            "NO_FILE_MATCH",
            "PARSING_ERROR",
            "STRING_CONVERSION_ERROR",
            "MORE_THAN_ONE_KEY_MATCH"
        ]
        GENERAL_EXCEPTIONS = [
            "ZIP_READ_FAIL",
            "FILE_PROCESSING_FAIL_GENERAL",
        ]
        BLUEPRINT_EXCEPTIONS.sort()
        GENERAL_EXCEPTIONS.sort()

        exc_per_module = {}

        # Only include classrooms belonging to actual users (not superusers)
        classrooms = Classroom.objects.exclude(
            Q(is_test_participation_class=True) |
            Q(owner__is_staff=True)
        ).select_related('base_module').all()

        base_modules = BaseModule.objects.all()
        for module in base_modules:
            exc_per_module[module.name] = {}

            # Gather general information.
            classroom_ids = classrooms.filter(
                base_module=module).values_list('url_id', flat=True)
            donation_project = DonationProject.objects.filter(
                url_id=module.ddm_project_id).first()
            participants = Participant.objects.filter(
                project=donation_project,
                extra_data__url_param__class__in=classroom_ids
            )

            # Add module/uploader-level exceptions
            general_exception_counts = {exc: 0 for exc in GENERAL_EXCEPTIONS}

            general_actual_counts = ExceptionLogEntry.objects.filter(
                exception_type__in=GENERAL_EXCEPTIONS,
                participant__in=participants,
                blueprint=None
            ).values('exception_type').annotate(
                count=Count('participant', distinct=True)
            ).values_list('exception_type', 'count')

            general_exception_counts.update(general_actual_counts)

            exc_per_module[module.name]['general'] = general_exception_counts.copy()

            # Add blueprint-level exceptions
            blueprints = DonationBlueprint.objects.filter(
                project=donation_project)

            blueprint_exceptions = {}
            for blueprint in blueprints:
                bp_exception_counts = {exc: 0 for exc in BLUEPRINT_EXCEPTIONS}

                bp_actual_counts = ExceptionLogEntry.objects.filter(
                    exception_type__in=BLUEPRINT_EXCEPTIONS,
                    participant__in=participants,
                    blueprint=blueprint
                ).values('exception_type').annotate(
                    count=Count('participant', distinct=True)
                ).values_list('exception_type', 'count')

                bp_exception_counts.update(bp_actual_counts)

                blueprint_exceptions[blueprint.name] = bp_exception_counts.copy()

            exc_per_module[module.name]['blueprints'] = blueprint_exceptions
            exc_per_module[module.name]['id'] = module.pk

        context['blueprint_exceptions'] = BLUEPRINT_EXCEPTIONS
        context['general_exceptions'] = GENERAL_EXCEPTIONS
        context['exceptions_per_module'] = exc_per_module

        return context
