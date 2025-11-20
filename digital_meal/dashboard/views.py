from ddm.apis.serializers import ResponseSerializer
from ddm.datadonation.models import DonationBlueprint
from ddm.participation.models import Participant
from ddm.projects.models import DonationProject
from ddm.questionnaire.models import QuestionnaireResponse
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import UserPassesTestMixin
from django.db.models import Count, Q
from django.utils import timezone
from django.views.generic import TemplateView

from digital_meal.tool.models import Classroom, Teacher, BaseModule

User = get_user_model()


class DashboardView(UserPassesTestMixin, TemplateView):
    template_name = 'dashboard/dashboard.html'

    def test_func(self):
        """Requesting user must pass this test to access view."""
        return self.request.user.is_staff

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        time_now = timezone.now()

        # Classroom statistics
        classrooms = Classroom.objects.exclude(
            Q(is_test_participation_class=True) |
            Q(owner__is_staff=True)
        )

        context['total_classrooms'] = classrooms.count()
        context['active_classrooms'] = classrooms.filter(
            expiry_date__gte=time_now
        ).count()
        context['expired_classrooms'] = classrooms.filter(
            expiry_date__lt=time_now
        ).count()

        context['classrooms_by_module'] = classrooms.values(
            'base_module__name'
        ).annotate(
            count=Count('id'),
            n_active=Count('id', filter=Q(expiry_date__gte=time_now)),
            n_expired=Count('id', filter=Q(expiry_date__lt=time_now)),
        ).order_by('-count')

        context['recent_classrooms'] = classrooms.select_related(
            'owner', 'owner__teacher', 'base_module'
        ).order_by('-date_created')[:10]

        # Teacher statistics
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


class ParticipantStatsView(UserPassesTestMixin, TemplateView):
    """HTMX endpoint for loading participant statistics."""
    template_name = 'dashboard/partials/participant_stats.html'

    def test_func(self):
        """Requesting user must pass this test to access view."""
        return self.request.user.is_staff

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Aggregate participant statistics by module
        info_per_module = {}

        classrooms = Classroom.objects.exclude(
            Q(is_test_participation_class=True) |
            Q(owner__is_staff=True)
        ).select_related('base_module').all()

        base_modules = BaseModule.objects.all()
        for module in base_modules:
            module_name = module.name
            info_per_module[module_name] = {}

            # Gather base information
            classroom_ids = classrooms.filter(base_module=module).values_list('url_id', flat=True)
            donation_project = DonationProject.objects.filter(url_id=module.ddm_project_id).first()

            # Get all participants for relevant classroom
            participants = Participant.objects.filter(
                project=donation_project,
                extra_data__url_param__class__in=classroom_ids
            )

            # Get overall participation counts
            n_classrooms = len(classroom_ids)
            n_started = participants.count()
            n_completed = participants.filter(completed=True).count()

            # Loop over blueprints to gather blueprint specific stats
            info_per_module[module_name]['blueprints'] = {}
            blueprints = DonationBlueprint.objects.filter(project=donation_project)
            for blueprint in blueprints:
                n_submitted = blueprint.datadonation_set.filter(
                    participant__in=participants, status='success'
                ).count()

                # Check donation consent
                responses = QuestionnaireResponse.objects.filter(participant__in=participants)
                response_data = ResponseSerializer(responses, many=True).data
                n_agreed_to_donate = 0
                for response in response_data:
                    usage_dd_consent = response['response_data'].get('usage_dd_consent')
                    if usage_dd_consent in [1, '1']:
                        n_agreed_to_donate += 1

                if n_submitted > 0:
                    donation_rate = n_agreed_to_donate / n_submitted
                else:
                    donation_rate = 0

                blueprint_stats = {
                    'n_submitted': n_submitted,
                    'n_donated': n_agreed_to_donate,
                    'donation_rate': donation_rate
                }

                info_per_module[module_name]['blueprints'][blueprint.name] = blueprint_stats

            info_per_module[module_name].update({
                'classrooms': n_classrooms,
                'total': n_started,
                'completed': n_completed,
            })

        # Calculate completion rates and averages
        total_participants = 0
        total_completed = 0

        for module_data in info_per_module.values():
            if module_data['total'] > 0:
                module_data['completion_rate'] = (module_data['completed'] / module_data['total']) * 100
                module_data['avg_per_classroom'] = module_data['total'] / module_data['classrooms']
                total_participants += module_data['total']
            else:
                module_data['completion_rate'] = 0
                module_data['avg_per_classroom'] = 0

            total_completed += module_data['completed']

        context['total_participants'] = total_participants
        context['total_completed'] = total_completed
        context['completion_rate'] = (total_completed / total_participants * 100) if total_participants > 0 else 0
        context['avg_per_classroom'] = total_participants / classrooms.count() if classrooms.count() > 0 else 0
        context['participants_by_module'] = info_per_module

        return context
