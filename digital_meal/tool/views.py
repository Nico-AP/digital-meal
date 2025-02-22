from ddm.datadonation.models import DonationBlueprint
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import TemplateView, ListView, DetailView
from django.views.generic.edit import CreateView, UpdateView

from .forms import ClassroomCreateForm, ClassroomTrackForm
from .models import Classroom, Teacher, MainTrack


class OwnershipRequiredMixin:
    """
    Mixin to only allow access to objects that are owned by the current user.
    Superuser can access any object.
    """
    def dispatch(self, request, *args, **kwargs):
        classroom_id = self.kwargs.get('url_id', None)
        if classroom_id is None:
            raise Http404()

        classroom = get_object_or_404(Classroom, url_id=classroom_id)

        if classroom.owner == request.user or request.user.is_superuser:
            return super().dispatch(request, *args, **kwargs)

        raise PermissionDenied()


class ProfileView(LoginRequiredMixin, TemplateView):
    template_name = 'tool/profile.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context['teacher'] = Teacher.objects.filter(user=user).first()
        return context


class ToolMainPage(LoginRequiredMixin, ListView):
    """ Show overview for a specific user. """
    model = Classroom
    template_name = 'tool/main_page.html'

    def get_queryset(self):
        return Classroom.objects.filter(owner=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['active_classes'] = [
            c for c in context['object_list'] if c.is_active]
        context['archived_classes'] = [
            c for c in context['object_list'] if not c.is_active]
        return context


class ClassroomDetail(OwnershipRequiredMixin, LoginRequiredMixin, DetailView):
    """ Display participation overview statistics for a classroom. """
    model = Classroom
    lookup_field = 'url_id'
    slug_field = 'url_id'
    slug_url_kwarg = 'url_id'
    template_name = 'tool/class/detail.html'

    def dispatch(self, request, *args, **kwargs):
        obj = self.get_object()
        if not obj.track:
            return redirect(reverse_lazy('class_assign_track',
                                         kwargs={'url_id': obj.url_id}))

        if not obj.is_active:
            return redirect(reverse_lazy('class_expired',
                                         kwargs={'url_id': obj.url_id}))

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(self.get_overview_data())
        context['main_track'] = self.object.track
        context['sub_tracks'] = self.object.sub_tracks.all()
        return context

    def get_overview_data(self):
        """
        Returns a dictionary holding information on how many participants
        have taken part in a data donation project for the given classroom.
        """
        participants = self.object.get_classroom_participants()

        if not participants.exists():
            return {}

        # Compute basic participation statistics.
        participant_ids = participants.values_list('id', flat=True)
        n_started = len(participants)
        n_finished = len(participants.filter(completed=True))

        # Compute donation statistics.
        donation_project = self.object.get_related_donation_project()
        n_donations = {}
        donation_dates = []
        blueprints = DonationBlueprint.objects.filter(project=donation_project)
        for blueprint in blueprints:
            blueprint_donations = blueprint.datadonation_set.filter(
                participant__pk__in=participant_ids, status='success'
            ).defer('data')

            n_donations[blueprint.name] = len(blueprint_donations)
            donation_dates.extend(blueprint_donations.values_list(
                'time_submitted', flat=True))

        data = {
            'n_donations': n_donations,
            'n_not_finished': (n_started - n_finished),
            'n_finished': n_finished,
            'donation_dates': [
                d.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
                for d in list(set(donation_dates))
            ]
        }
        return data


class ClassroomCreate(LoginRequiredMixin, CreateView):
    """ Register a new classroom. """
    model = Classroom
    template_name = 'tool/class/create.html'
    form_class = ClassroomCreateForm

    def form_valid(self, form):
        form.instance.owner = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy(
            'class_assign_track', kwargs={'url_id': self.object.url_id})


class ClassroomAssignTrack(LoginRequiredMixin, UpdateView):
    """ Assign a track to a classroom. """
    model = Classroom
    lookup_field = 'url_id'
    slug_field = 'url_id'
    slug_url_kwarg = 'url_id'
    template_name = 'tool/class/assign_track.html'
    form_class = ClassroomTrackForm

    def dispatch(self, request, *args, **kwargs):
        # If classroom has track already assigned, redirect to overview
        obj = self.get_object()
        if obj.track:
            return redirect(reverse_lazy('class_detail',
                                         kwargs={'url_id': obj.url_id}))
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.owner = self.request.user
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        active_main_tracks = MainTrack.objects.filter(active=True)
        context['active_main_tracks'] = active_main_tracks
        return context


class ClassroomExpired(LoginRequiredMixin, OwnershipRequiredMixin, TemplateView):
    template_name = 'tool/class/expired.html'


class ClassroomDoesNotExist(LoginRequiredMixin, TemplateView):
    template_name = 'tool/class/does_not_exist.html'


class TeacherEdit(LoginRequiredMixin, UpdateView):
    """ Edit teacher account details. """
    model = Teacher
    fields = []
    template_name = 'website/form.html'

    def dispatch(self, request, *args, **kwargs):
        """ Make sure users can only edit their own profile. """
        teacher_id = self.kwargs.get('id', None)
        if teacher_id is None:
            raise Http404()

        teacher = get_object_or_404(Teacher, user=request.user)

        if teacher.user == request.user or request.user.is_superuser:
            return super().dispatch(request, *args, **kwargs)

        raise Http404()
