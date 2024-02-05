import requests

from django.conf import settings
from django.views.generic import TemplateView, DetailView

from digital_meal.models import Classroom
from digital_meal.utils import yt_data, yt_plots


class ClassroomReport(DetailView):
    """ Generate class report. """
    model = Classroom
    template_name = 'digital_meal/reports/class_report_youtube.html'

    def get_data(self):
        api_endpoint = self.object.track.ddm_api_endpoint
        api_token = self.object.track.ddm_api_token

        headers = {
            'Authorization': f'Token {api_token}'
        }
        payload = {
            'dmclsrm': self.object.pool_id,
        }
        r = requests.get(api_endpoint, headers=headers, params=payload)

        if r.ok:
            return r.json()
        else:
            return None

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        data = self.get_data()

        context['data'] = data
        return context


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
        project_id = 'dm-track1'
        watch_history = self.get_donation_data(
            project_id, participant_id, blueprint_id=1)
        watch_history = watch_history['Angesehene Videos'][0]
        # subscriptions = self.get_donation_data(
        #     project_id, participant_id, blueprint_id=17)
        search_history = self.get_donation_data(
            project_id, participant_id, blueprint_id=2)
        search_history = search_history['Suchverlauf'][0]

        # 2) get and transform all data series
        watched_videos = yt_data.exclude_google_ads_videos(watch_history)
        dates = yt_data.get_date_list(watched_videos)
        date_range = max(dates) - min(dates)
        n_videos_total = len(watched_videos)

        fav_video = yt_data.get_most_watched_video(watched_videos)
        video_titles = yt_data.get_video_title_dict(watched_videos)
        fav_video['title'] = video_titles.get(fav_video['id'])

        channels = yt_data.get_channels_from_history(watched_videos)
        search_dates = yt_data.get_date_list(search_history)

        search_terms = yt_data.get_search_term_frequency(search_history, 15)

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
            'n_searches': len(search_history),
            'searches': search_terms,
            'search_plot': yt_plots.get_searches_plot(search_history),
            'n_videos_liked': 0,
            'share_videos_liked': 0
        })
        return context
