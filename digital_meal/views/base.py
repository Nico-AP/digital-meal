import requests

from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView, ListView, DetailView
from django.views.generic.edit import CreateView, UpdateView

from digital_meal.forms import ClassroomCreateForm, ClassroomTrackForm
from digital_meal.models import Classroom, User, Teacher


class OwnershipRequiredMixin:
    """
    Mixin to only allow access to objects that are owned by the current user.
    Superuser can access any object.
    """
    def dispatch(self, request, *args, **kwargs):
        classroom_id = self.kwargs.get('id', None)
        if classroom_id is None:
            raise Http404()

        try:
            classroom = Classroom.objects.get(id=classroom_id)
        except Classroom.DoesNotExist:
            raise Http404()

        if classroom.owner == request.user or request.user.is_superuser:
            return super().dispatch(request, *args, **kwargs)
        else:
            raise PermissionDenied()


class ProfileView(LoginRequiredMixin, TemplateView):
    template_name = 'digital_meal/profile.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context['teacher'] = Teacher.objects.filter(user=user).first()
        return context


class ProfileOverview(ListView, LoginRequiredMixin):
    """ Show overview for a specific user. """
    model = Classroom
    template_name = 'digital_meal/overview.html'

    def get_queryset(self):
        return Classroom.objects.filter(owner=self.request.user)


class ClassroomDetail(DetailView, OwnershipRequiredMixin, LoginRequiredMixin):
    """ Display participation overview statistics for a classroom. """
    model = Classroom
    template_name = 'digital_meal/classroom_detail.html'

    def dispatch(self, request, *args, **kwargs):
        obj = self.get_object()
        if not obj.track:
            return redirect(reverse_lazy('classroom-assign-track', kwargs={'pk': obj.pk}))

        if obj.expiry_date < timezone.now():
            return redirect(reverse_lazy('classroom-expired', kwargs={'pk': obj.pk}))

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['participation_stats'] = self.get_participation_data(self.object)
        return context

    @staticmethod
    def get_participation_data(classroom):
        """
        Gets participation data by querying the participation API endpoint of a
        DDM instance that has ddm-pooled enabled.
        """
        api_endpoint = settings.DDM_PARTICIPANT_ENDPOINT
        api_token = settings.DDM_API_TOKEN

        headers = {
            'Authorization': f'Token {api_token}'
        }
        payload = {
            'project': classroom.track.ddm_project_id,
            'pool': classroom.pool_id
        }
        try:
            r = requests.get(api_endpoint, headers=headers, params=payload)
            return r.json()
        except:  # requests.ConnectionError:
            return None


class ClassroomCreate(CreateView, LoginRequiredMixin):
    """ Register a new classroom. """
    model = Classroom
    template_name = 'digital_meal/classroom_create.html'
    form_class = ClassroomCreateForm

    def form_valid(self, form):
        form.instance.owner = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('classroom-assign-track', kwargs={'pk': self.object.pk})


class ClassroomAssignTrack(UpdateView, LoginRequiredMixin):
    """ Assign a track to a classroom. """
    model = Classroom
    template_name = 'digital_meal/classroom_create_track.html'
    form_class = ClassroomTrackForm

    def dispatch(self, request, *args, **kwargs):
        # If classroom has track already assigned, redirect to overview
        obj = self.get_object()
        if obj.track:
            return redirect(reverse_lazy('classroom-detail', kwargs={'pk': obj.pk}))
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.owner = self.request.user
        return super().form_valid(form)


class ClassroomExpired(LoginRequiredMixin, OwnershipRequiredMixin, TemplateView):
    template_name = 'digital_meal/classroom_expired.html'


class TeacherEdit(UpdateView, LoginRequiredMixin):
    """ Edit teacher account details. """
    model = Teacher
    fields = []
    template_name = 'digital_meal/form.html'

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


@method_decorator(staff_member_required, name='dispatch')
class StyleGuide(TemplateView):
    template_name = 'digital_meal/styleguide.html'
