from io import BytesIO

import requests

from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404, HttpResponse
from django.template.loader import get_template
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView, ListView, DetailView
from django.views.generic.edit import CreateView, UpdateView

from digital_meal.forms import ClassroomCreateForm
from digital_meal.models import Classroom, User, Teacher
from digital_meal.utils import yt_data, yt_plots
from xhtml2pdf import pisa


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
            raise Http404()


class MainView(TemplateView):
    template_name = 'digital_meal/base.html'


class ProfileView(LoginRequiredMixin, TemplateView):
    template_name = 'digital_meal/profile.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context['teacher'] = Teacher.objects.filter(user=user).first()
        return context


class ClassroomList(ListView, LoginRequiredMixin):
    """ List classrooms registered by a specific user. """
    model = Classroom
    template_name = 'digital_meal/classroom_list.html'

    def get_queryset(self):
        return Classroom.objects.filter(owner=self.request.user)


class ClassroomDetail(DetailView, OwnershipRequiredMixin, LoginRequiredMixin):
    """ Display participation overview statistics for a classroom. """
    model = Classroom
    template_name = 'digital_meal/classroom_detail.html'

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
            'project': classroom.track.module.ddm_external_project_id,
            'pool': classroom.pool_id
        }
        try:
            r = requests.get(api_endpoint, headers=headers, params=payload)
            return r.json()
        except requests.ConnectionError:
            return None


class ClassroomCreate(CreateView, LoginRequiredMixin):
    """ Register a new classroom. """
    model = Classroom
    template_name = 'digital_meal/classroom_create.html'
    form_class = ClassroomCreateForm

    def form_valid(self, form):
        form.instance.owner = self.request.user
        return super().form_valid(form)


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


class IndividualReport(TemplateView):
    """ Generates an individual report. """
    template_name = 'digital_meal/individual_report.html'

    @staticmethod
    def get_donation_data(project_id, participant_id, blueprint_id):
        """
        Gets participation data by querying the participation API endpoint of a
        DDM instance that has ddm-pooled enabled.

        Passes the 'external pool project id', the 'external pool participant id'
        and a blueprint id as query parameters.
        """
        api_endpoint = settings.DDM_DONATION_ENDPOINT
        api_token = settings.DDM_API_TOKEN

        headers = {
            'Authorization': f'Token {api_token}'
        }
        payload = {
            'project': project_id,
            'participant': participant_id,
            'blueprint': blueprint_id
        }
        r = requests.get(api_endpoint, headers=headers, params=payload)

        if r.ok:
            return r.json()
        else:
            return None

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # 1) get data from api
        participant_id = self.kwargs['external_pool_participant_id']
        project_id = self.kwargs['external_pool_project_id']
        watch_history = self.get_donation_data(
            project_id, participant_id, blueprint_id=16)
        # subscriptions = self.get_donation_data(
        #     project_id, participant_id, blueprint_id=17)
        search_history = self.get_donation_data(
            project_id, participant_id, blueprint_id=31)

        # 2) get and transform all data series
        watched_videos = yt_data.exclude_google_ads_videos(watch_history['data'])
        dates = yt_data.get_date_list(watched_videos)
        date_range = max(dates) - min(dates)
        n_videos_total = len(watched_videos)

        fav_video = yt_data.get_most_watched_video(watched_videos)
        video_titles = yt_data.get_video_title_dict(watched_videos)
        fav_video['title'] = video_titles.get(fav_video['id'])

        channels = yt_data.get_channels_from_history(watched_videos)
        search_dates = yt_data.get_date_list(search_history['data'])

        search_terms = yt_data.get_search_term_frequency(search_history['data'], 15)

        # 3) add to context
        context.update({
            'dates_plot': yt_plots.get_timeseries_plot(dates),
            'weekday_use_plot': yt_plots.get_weekday_use_plot(dates),
            'hours_plot': yt_plots.get_day_usetime_plot(dates),
            'channel_plot': yt_plots.get_channel_plot(channels),
            'n_distinct_channels': len(set(channels)),
            'date_first': min(dates),
            'date_last': max(dates),
            'n_videos_mean': round((n_videos_total / date_range.days), 2),
            'n_videos_total': n_videos_total,
            'fav_video': fav_video,
            'date_first_search': min(search_dates),
            'n_searches': len(search_history['data']),
            'searches': search_terms,
            'search_plot': yt_plots.get_searches_plot(search_history['data']),
            'n_videos_liked': 0,
            'share_videos_liked': 0
        })
        return context


# TODO: Finish this view.
class IndividualReportPDF(IndividualReport):

    def get(self, request, *args, **kwargs):
        template = get_template(self.template_name)
        context = self.get_context_data()
        html = template.render(context)
        pdf = BytesIO()
        pisa.pisaDocument(BytesIO(html.encode('ISO-8859-1')), pdf)
        response = HttpResponse(pdf.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename=individual_report.pdf'
        return response


@method_decorator(staff_member_required, name='dispatch')
class StyleGuide(TemplateView):
    template_name = 'digital_meal/styleguide.html'
