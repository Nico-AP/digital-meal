from uuid import UUID

from ddm.apis.serializers import ResponseSerializer
from ddm.datadonation.models import DataDonation, DonationBlueprint
from ddm.logging.models import ExceptionLogEntry
from ddm.participation.models import Participant
from ddm.projects.models import DonationProject
from ddm.questionnaire.models import QuestionnaireResponse
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import UserPassesTestMixin
from django.db.models import Count, Q, QuerySet, Value
from django.db.models.functions import Concat
from django.utils import timezone
from django.views.generic import TemplateView

from digital_meal.tool.models import BaseModule, Classroom, Teacher

User = get_user_model()


class DashboardView(UserPassesTestMixin, TemplateView):
    template_name = "dashboard/dashboard.html"

    def test_func(self):
        """Requesting user must pass this test to access view."""
        return self.request.user.is_staff


class ClassroomOverviewView(UserPassesTestMixin, TemplateView):
    """HTMX endpoint for loading participant statistics."""

    template_name = "dashboard/partials/classroom_overview.html"

    def test_func(self):
        """Requesting user must pass this test to access view."""
        return self.request.user.is_staff

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        time_now = timezone.now()

        classrooms = Classroom.objects.exclude(
            Q(is_test_participation_class=True) | Q(owner__is_staff=True)
        )

        # Overview
        context["total_classrooms"] = classrooms.count()
        context["active_classrooms"] = classrooms.filter(
            expiry_date__gte=time_now
        ).count()
        context["expired_classrooms"] = classrooms.filter(
            expiry_date__lt=time_now
        ).count()

        # By Module
        context["classrooms_by_module"] = (
            classrooms.values("base_module__name")
            .annotate(
                count=Count("id"),
                n_active=Count("id", filter=Q(expiry_date__gte=time_now)),
                n_expired=Count("id", filter=Q(expiry_date__lt=time_now)),
            )
            .order_by("-count")
        )

        # By Submodule
        context["classrooms_by_submodule"] = (
            classrooms.values("sub_modules__pk")
            .annotate(
                name=Concat("base_module__name", Value(": "), "sub_modules__name"),
                count=Count("id"),
                n_active=Count("id", filter=Q(expiry_date__gte=time_now)),
                n_expired=Count("id", filter=Q(expiry_date__lt=time_now)),
            )
            .order_by("-count")
        )

        # By Level
        context["classrooms_by_level"] = (
            classrooms.values("school_level")
            .annotate(
                count=Count("id"),
                n_active=Count("id", filter=Q(expiry_date__gte=time_now)),
                n_expired=Count("id", filter=Q(expiry_date__lt=time_now)),
            )
            .order_by("school_level")
        )

        # By Subject
        context["classrooms_by_subject"] = (
            classrooms.values("subject")
            .annotate(
                count=Count("id"),
                n_active=Count("id", filter=Q(expiry_date__gte=time_now)),
                n_expired=Count("id", filter=Q(expiry_date__lt=time_now)),
            )
            .order_by("subject")
        )

        # By Instruction Format
        context["classrooms_by_format"] = (
            classrooms.values("instruction_format")
            .annotate(
                count=Count("id"),
                n_active=Count("id", filter=Q(expiry_date__gte=time_now)),
                n_expired=Count("id", filter=Q(expiry_date__lt=time_now)),
            )
            .order_by("instruction_format")
        )

        context["recent_classrooms"] = classrooms.select_related(
            "owner", "owner__teacher", "base_module"
        ).order_by("-date_created")[:10]

        return context


class TeacherOverviewView(UserPassesTestMixin, TemplateView):
    """HTMX endpoint for loading participant statistics."""

    template_name = "dashboard/partials/teacher_overview.html"

    def test_func(self):
        """Requesting user must pass this test to access view."""
        return self.request.user.is_staff

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        teacher_users = User.objects.exclude(is_staff=True)
        teachers = Teacher.objects.filter(user__in=teacher_users)

        context["teachers_with_classroom"] = (
            teacher_users.filter(classroom__isnull=False).distinct().count()
        )

        context["teachers_without_classroom"] = teacher_users.filter(
            classroom__isnull=True
        ).count()

        context["recent_teachers"] = teacher_users.select_related("teacher").order_by(
            "-date_joined"
        )[:10]

        context["teachers_by_canton"] = (
            teachers.values("canton")
            .annotate(count=Count("id"))
            .order_by("-count")[:10]
        )

        return context


class ParticipationOverviewView(UserPassesTestMixin, TemplateView):
    """HTMX endpoint for loading participant statistics."""

    template_name = "dashboard/partials/participation_overview.html"

    def test_func(self):
        """Requesting user must pass this test to access view."""
        return self.request.user.is_staff

    def get_classrooms(self) -> QuerySet[Classroom]:
        classrooms = (
            Classroom.objects.exclude(
                Q(is_test_participation_class=True) | Q(owner__is_staff=True)
            )
            .select_related("base_module")
            .all()
        )
        return classrooms

    def group_classrooms_by_module(
        self, classrooms: QuerySet[Classroom]
    ) -> dict[UUID, list[Classroom]]:
        result = {}
        for classroom in classrooms:
            if classroom.base_module is None:
                continue
            module_id = classroom.base_module.id
            if module_id not in result:
                result[module_id] = []
            result[module_id].append(classroom.url_id)
        return result

    def get_relevant_projects(
        self, base_modules: QuerySet[BaseModule]
    ) -> QuerySet[DonationProject]:
        """Get projects related to base modules."""
        project_ids = [m.ddm_project_id for m in base_modules if m.ddm_project_id]
        return DonationProject.objects.filter(url_id__in=project_ids).prefetch_related(
            "donationblueprint_set"
        )

    def get_relevant_participants(
        self,
        donation_projects: QuerySet[DonationProject],
        classrooms: QuerySet[Classroom],
    ) -> list[Participant]:
        """Get participants of selected classrooms."""

        all_participants = list(
            Participant.objects.filter(project__in=donation_projects).select_related(
                "project"
            )
        )

        relevant_participants = [
            p
            for p in all_participants
            if p.extra_data.get("url_param", {}).get("class")
            in classrooms.values_list("url_id", flat=True)
        ]
        return relevant_participants

    def group_participants_by_project(
        self, participants: list[Participant]
    ) -> dict[str, list[Participant]]:
        result = {}
        for participant in participants:
            project_id = participant.project.url_id
            if project_id not in result:
                result[project_id] = []
            result[project_id].append(participant)
        return result

    def group_donations_by_blueprint(
        self,
        donation_projects: QuerySet[DonationProject],
        participants: list[Participant],
    ) -> dict[int, list[str]]:
        donation_info = DataDonation.objects.filter(
            project__in=donation_projects,
            status="success",
            consent=True,
            participant__in=participants,
        ).values("blueprint_id", "participant__external_id")

        result = {}
        for donation in donation_info:
            blueprint_id = donation["blueprint_id"]
            if blueprint_id not in result:
                result[blueprint_id] = []
            result[blueprint_id].append(donation["participant__external_id"])
        return result

    def get_consent_lookup(self, participants: list[Participant]) -> set:
        relevant_responses = QuestionnaireResponse.objects.filter(
            participant__in=participants
        )
        response_data = ResponseSerializer(relevant_responses, many=True).data

        return {
            response["participant"]
            for response in response_data
            if response["response_data"].get("usage_dd_consent") in [1, "1"]
        }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        base_modules = BaseModule.objects.all()

        classrooms = self.get_classrooms()
        classrooms_by_module = self.group_classrooms_by_module(classrooms)

        donation_projects = self.get_relevant_projects(base_modules)
        projects_by_url_id = {p.url_id: p for p in donation_projects}

        relevant_participants = self.get_relevant_participants(
            donation_projects, classrooms
        )

        participants_by_project_id = self.group_participants_by_project(
            relevant_participants
        )

        donations_by_blueprint_id = self.group_donations_by_blueprint(
            donation_projects, relevant_participants
        )

        consented_participant_ids = self.get_consent_lookup(relevant_participants)

        info_per_module = {}
        for module in base_modules:
            module_name = module.name

            # Gather base information
            classroom_ids = classrooms_by_module.get(module.id, [])
            donation_project = projects_by_url_id.get(module.ddm_project_id)

            if not donation_project:
                continue

            # Single query for all participant stats
            project_participants = participants_by_project_id.get(
                donation_project.url_id, []
            )
            relevant_participant_ids = {p.external_id for p in project_participants}

            # Process blueprints to gather blueprint specific stats
            blueprints_info = {}
            blueprints = donation_project.donationblueprint_set.all()

            for blueprint in blueprints:
                uploaded_participant_ids = set(
                    donations_by_blueprint_id.get(blueprint.id, [])
                )
                uploaded_participant_ids = (
                    uploaded_participant_ids & relevant_participant_ids
                )

                n_uploaded = len(uploaded_participant_ids)

                # Check donation consent
                n_agreed_to_donate = len(
                    uploaded_participant_ids & consented_participant_ids
                )

                donation_rate = (
                    (n_agreed_to_donate / n_uploaded) if n_uploaded > 0 else 0
                )

                blueprints_info[blueprint.name] = {
                    "n_uploaded": n_uploaded,
                    "n_donated": n_agreed_to_donate,
                    "donation_rate": donation_rate,
                }

            # Get overall participation counts
            n_classrooms = len(classroom_ids)
            n_started = len(project_participants)
            n_completed = sum(1 for p in project_participants if p.completed)

            info_per_module[module_name] = {
                "id": module.pk,
                "classrooms": n_classrooms,
                "total": n_started,
                "completed": n_completed,
                "completion_rate": (n_completed / n_started * 100)
                if n_started > 0
                else 0,
                "avg_per_classroom": n_started / n_classrooms
                if n_classrooms > 0
                else 0,
                "blueprints": blueprints_info,
            }

        # Calculate totals
        total_participants = sum(m["total"] for m in info_per_module.values())
        total_completed = sum(m["completed"] for m in info_per_module.values())
        total_classrooms = classrooms.count()

        context["total_participants"] = total_participants
        context["total_completed"] = total_completed
        context["completion_rate"] = (
            (total_completed / total_participants * 100)
            if total_participants > 0
            else 0
        )
        context["avg_per_classroom"] = (
            total_participants / total_classrooms if total_classrooms > 0 else 0
        )
        context["participants_by_module"] = dict(sorted(info_per_module.items()))

        return context


class ExceptionOverviewView(UserPassesTestMixin, TemplateView):
    """HTMX endpoint for loading exception statistics."""

    template_name = "dashboard/partials/exception_overview.html"

    def test_func(self):
        """Requesting user must pass this test to access view."""
        return self.request.user.is_staff

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        blueprint_exception_types = [
            "NO_FILE_MATCH",
            "PARSING_ERROR",
            "STRING_CONVERSION_ERROR",
            "MORE_THAN_ONE_KEY_MATCH",
        ]
        general_exception_types = [
            "ZIP_READ_FAIL",
            "FILE_PROCESSING_FAIL_GENERAL",
        ]
        blueprint_exception_types.sort()
        general_exception_types.sort()

        exc_per_module = {}

        # Only include classrooms belonging to actual users (not superusers)
        classrooms = (
            Classroom.objects.exclude(
                Q(is_test_participation_class=True) | Q(owner__is_staff=True)
            )
            .select_related("base_module")
            .all()
        )

        base_modules = BaseModule.objects.all()
        for module in base_modules:
            exc_per_module[module.name] = {}

            # Gather general information.
            classroom_ids = classrooms.filter(base_module=module).values_list(
                "url_id", flat=True
            )
            donation_project = DonationProject.objects.filter(
                url_id=module.ddm_project_id
            ).first()
            participants = Participant.objects.filter(
                project=donation_project, extra_data__url_param__class__in=classroom_ids
            )

            # Add module/uploader-level exceptions
            general_exception_counts = {exc: 0 for exc in general_exception_types}

            general_actual_counts = (
                ExceptionLogEntry.objects.filter(
                    exception_type__in=general_exception_types,
                    participant__in=participants,
                    blueprint=None,
                )
                .values("exception_type")
                .annotate(count=Count("participant", distinct=True))
                .values_list("exception_type", "count")
            )

            general_exception_counts.update(general_actual_counts)

            exc_per_module[module.name]["general"] = general_exception_counts.copy()

            # Add blueprint-level exceptions
            blueprints = DonationBlueprint.objects.filter(project=donation_project)

            blueprint_exceptions = {}
            for blueprint in blueprints:
                bp_exception_counts = {exc: 0 for exc in blueprint_exception_types}

                bp_actual_counts = (
                    ExceptionLogEntry.objects.filter(
                        exception_type__in=blueprint_exception_types,
                        participant__in=participants,
                        blueprint=blueprint,
                    )
                    .values("exception_type")
                    .annotate(count=Count("participant", distinct=True))
                    .values_list("exception_type", "count")
                )

                bp_exception_counts.update(bp_actual_counts)

                blueprint_exceptions[blueprint.name] = bp_exception_counts.copy()

            exc_per_module[module.name]["blueprints"] = blueprint_exceptions
            exc_per_module[module.name]["id"] = module.pk

        context["blueprint_exceptions"] = blueprint_exception_types
        context["general_exceptions"] = general_exception_types
        context["exceptions_per_module"] = exc_per_module

        return context
