import json

import requests

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import TemplateView, ListView, DetailView
from django.views.generic.edit import CreateView, UpdateView
from requests import JSONDecodeError

from .forms import ClassroomCreateForm, ClassroomTrackForm
from .models import Classroom, Teacher, MainTrack


class OwnershipRequiredMixin:
    """
    Mixin to only allow access to objects that are owned by the current user.
    Superuser can access any object.
    """
    def dispatch(self, request, *args, **kwargs):
        classroom_id = self.kwargs.get('id', None)
        if classroom_id is None:
            classroom_id = self.kwargs.get('pk', None)
        if classroom_id is None:
            raise Http404()

        try:
            classroom = Classroom.objects.get(id=classroom_id)
        except Classroom.DoesNotExist:
            return redirect('class_not_found')

        if classroom.owner == request.user or request.user.is_superuser:
            return super().dispatch(request, *args, **kwargs)
        else:
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
        context['active_classes'] = [c for c in context['object_list'] if c.is_active]
        context['archived_classes'] = [c for c in context['object_list'] if not c.is_active]
        return context


class ClassroomDetail(DetailView, OwnershipRequiredMixin, LoginRequiredMixin):
    """ Display participation overview statistics for a classroom. """
    model = Classroom
    template_name = 'tool/class/detail.html'

    def dispatch(self, request, *args, **kwargs):
        obj = self.get_object()
        if not obj.track:
            return redirect(reverse_lazy('class_assign_track', kwargs={'pk': obj.pk}))

        if obj.expiry_date < timezone.now():
            return redirect(reverse_lazy('class_expired', kwargs={'pk': obj.pk}))

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        overview_data = json.loads(self.get_overview_data())
        context.update(overview_data)
        context['main_track'] = self.object.track
        context['sub_tracks'] = self.object.sub_tracks.all()
        return context

    def get_overview_data(self):
        """ Retrieve overview data from DDM. """
        endpoint = self.object.track.overview_endpoint
        headers = {'Authorization': f'Token {self.object.track.ddm_api_token}'}
        payload = {'class': self.object.class_id}
        r = requests.get(endpoint, headers=headers, params=payload)

        if r.ok:
            try:
                return r.json()
            except JSONDecodeError:
                return '{}'
        else:
            return '{}'


class ClassroomCreate(CreateView, LoginRequiredMixin):
    """ Register a new classroom. """
    model = Classroom
    template_name = 'tool/class/create.html'
    form_class = ClassroomCreateForm

    def form_valid(self, form):
        form.instance.owner = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('class_assign_track', kwargs={'pk': self.object.pk})


class ClassroomAssignTrack(UpdateView, LoginRequiredMixin):
    """ Assign a track to a classroom. """
    model = Classroom
    template_name = 'tool/class/assign_track.html'
    form_class = ClassroomTrackForm

    def dispatch(self, request, *args, **kwargs):
        # If classroom has track already assigned, redirect to overview
        obj = self.get_object()
        if obj.track:
            return redirect(reverse_lazy('class_detail', kwargs={'pk': obj.pk}))
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


class TeacherEdit(UpdateView, LoginRequiredMixin):
    """ Edit teacher account details. """
    model = Teacher
    fields = []
    template_name = 'website/form.html'

    def dispatch(self, request, *args, **kwargs):
        """ Make sure users can only edit their own profile. """
        teacher_id = self.kwargs.get('id', None)
        if teacher_id is None:
            raise Http404()

        try:
            teacher = Teacher.objects.get(user=request.user)
        except Teacher.DoesNotExist:
            raise Http404()

        if teacher.user == request.user or request.user.is_superuser:
            return super().dispatch(request, *args, **kwargs)
        else:
            raise Http404()
