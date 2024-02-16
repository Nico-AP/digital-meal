import json

import pandas as pd
import requests
from django.urls import reverse_lazy

from django.utils import timezone
from django.views.generic import DetailView

from digital_meal.models import Classroom
from digital_meal.utils import yt_data, yt_plots


class DDMReport:

    def get_endpoint(self):
        """ Overwrite this method to return the API endpoint. """
        return ''

    def get_token(self):
        """ Overwrite this method to return the API token. """
        return ''

    def get_headers(self):
        return {'Authorization': f'Token {self.get_token()}'}

    def get_payload(self):
        return {}

    def get_data(self, payload=None):
        """ Retrieve data from DDM. """
        payload = self.get_payload() if payload is None else payload
        r = requests.get(self.get_endpoint(), headers=self.get_headers(), params=payload)

        if r.ok:
            return r.json()
        else:
            return None


class BaseClassroomReport(DDMReport, DetailView):
    """ Base class to generate a class report. """
    model = Classroom
    template_name = 'digital_meal/reports/youtube/class_report.html'

    def get_endpoint(self):
        return self.object.track.ddm_api_endpoint

    def get_token(self):
        return self.object.track.ddm_api_token

    def get_payload(self):
        return {'class': self.object.pool_id, }

    def get_data(self, payload=None):
        """ Retrieve data from DDM. """
        payload = self.get_payload() if payload is None else payload
        r = requests.get(self.get_endpoint(), headers=self.get_headers(), params=payload)

        if r.ok:
            return r.json()
        else:
            return {}


class ClassroomReportYouTube(BaseClassroomReport):
    """ Classroom report for the YouTube data. """
    model = Classroom
    template_name = 'digital_meal/reports/youtube/class_report.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        data = json.loads(self.get_data())

        if all(v is None for k, v in data['donations'].items()):
            self.template_name = 'digital_meal/reports/report_exception.html'
            context['exception_message'] = (
                'Es haben weniger als 5 Personen aus der Klasse ihre Daten '
                'hochgeladen.'
            )
            return context

        # Watch history (wh)
        context.update(self.get_watch_context(data['donations']['Angesehene Videos']))

        # Search history (sh)
        context.update(self.get_search_context(data['donations']['Suchverlauf']))

        # Subscribed channels (sc)
        context.update(self.get_subs_context(data['donations']['Abonnierte Kanäle']))

        n_donations = [len(v) for k, v in data['donations'].items() if v is not None]
        context['n_participants'] = max(n_donations)
        return context

    def get_watch_context(self, data):
        c = {}  # c = context
        if data is None:
            c['wh_available'] = False
            return c

        c['wh_available'] = True
        n_donations = len(data)

        wh_overall = []
        for entry in data:
            wh_overall += entry['data']
        wh_overall = yt_data.exclude_google_ads_videos(wh_overall)
        wh_overall_ids = yt_data.get_video_ids(wh_overall)
        c['n_vids_overall'] = len(wh_overall)
        c['n_vids_unique_overall'] = len(set(wh_overall_ids))
        c['n_vids_mean_overall'] = len(wh_overall) / n_donations

        interval_min = timezone.now() - timezone.timedelta(days=290)  # TODO: Adjust.
        wh_interval = yt_data.get_entries_in_date_range(wh_overall, interval_min)

        wh_interval_ids = yt_data.get_video_ids(wh_interval)
        c['n_vids_interval'] = len(wh_interval)
        c['n_vids_unique_interval'] = len(set(wh_interval_ids))
        c['n_vids_mean_interval'] = len(wh_interval) / n_donations

        wh_overall_dates = yt_data.get_date_list(wh_overall)
        # Barplot "n videos over the course of a year" - y: n_videos, x: dates
        c['dates_plot'] = yt_plots.get_timeseries_plot(wh_overall_dates)

        # Barplot "n videos per weekday" - y: n_videos, x: weekdays
        c['weekday_use_plot'] = yt_plots.get_weekday_use_plot(wh_overall_dates)

        # Heatmap "n videos per day per hour"
        c['hours_plot'] = yt_plots.get_day_usetime_plot(wh_overall_dates)
        return c

    def get_search_context(self, data):
        c = {}  # c = context
        if data is None:
            c['sh_available'] = False
            return c

        c['sh_available'] = True
        n_donations = len(data)

        sh_overall = []
        for entry in data:
            sh_overall += entry['data']

        sh_overall = yt_data.exclude_ads_from_search_history(sh_overall)
        sh_overall = yt_data.clean_search_titles(sh_overall)
        sh_overall_ids = yt_data.get_video_ids(sh_overall)
        c['n_searches_overall'] = len(sh_overall)
        c['n_searches_unique_overall'] = len(set(sh_overall_ids))
        c['n_searches_mean_overall'] = len(sh_overall) / n_donations

        interval_min = timezone.now() - timezone.timedelta(days=290)  # TODO: Adjust.
        sh_interval = yt_data.get_entries_in_date_range(sh_overall, interval_min)

        sh_interval_ids = yt_data.get_video_ids(sh_interval)
        c['n_search_interval'] = len(sh_interval)
        c['n_search_unique_interval'] = len(set(sh_interval_ids))
        c['n_search_mean_interval'] = len(sh_interval) / n_donations

        c['search_plot'] = yt_plots.get_searches_plot(sh_overall)
        return c

    def get_subs_context(self, data):

        def clean_channel_list(channel_list):
            keys = {
                'Channel ID|Kanal-ID|ID des cha.*|ID canale': 'id',
                'Channel title|Kanaltitel|Titres des cha.*|Titolo canale': 'title',
            }
            channels = []
            for channel in channel_list:
                for key, value in keys.items():
                    channel[value] = channel.pop(key, None)
                channels.append(channel)
            return channels

        c = {}  # c = context
        if data is None:
            c['sc_available'] = False
            return c

        c['sc_available'] = True
        n_donations = len(data)

        sc_overall = []
        for entry in data:
            sc_overall += entry['data']

        sc_overall = clean_channel_list(sc_overall)
        sc_titles = [entry['title'] for entry in sc_overall]

        c['n_subs'] = len(sc_overall)
        c['n_subs_unique'] = len(set(sc_titles))
        c['n_subs_mean'] = len(sc_overall) / n_donations

        subs_counts = pd.Series(sc_titles).value_counts()
        # subs_counts_relative = pd.Series(sc_titles).value_counts(normalize=True)
        n_subs_multiple = subs_counts[subs_counts > 1]
        c['n_subs_multiple'] = len(n_subs_multiple)
        c['most_popular_channels'] = subs_counts.nlargest(5).to_dict()
        return c


class BaseIndividualReport(DDMReport, DetailView):
    """ Base class to generate an individual report. """
    template_name = 'digital_meal/reports/youtube/individual_report.html'
    model = Classroom
    participant_id = None
    project_id = None

    def setup(self, request, *args, **kwargs):
        return super().setup(request, *args, **kwargs)

    def get_endpoint(self):
        return self.object.track.ddm_api_endpoint

    def get_token(self):
        return self.object.track.ddm_api_token

    def get_payload(self):
        payload = {'participant_id': self.kwargs.get('participant_id')}
        return payload


class IndividualReportYouTube(BaseIndividualReport):
    """ Base class to generate an individual report for the YouTube data. """
    template_name = 'digital_meal/reports/youtube/individual_report.html'

    def get_endpoint(self):
        kwargs = {'pk': self.object.pk}
        return self.request.build_absolute_uri(reverse_lazy('individual-data-api', kwargs=kwargs))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        data = json.loads(self.get_data())

        # Watch history
        context.update(self.get_watch_context(data['donations']['Angesehene Videos']))

        # Search history (sh)
        context.update(self.get_search_context(data['donations']['Suchverlauf']))

        return context

    def get_watch_context(self, data):
        c = {}  # c = context
        if data is None:
            c['watch_available'] = False
            return c

        c['watch_available'] = True
        watched_videos = yt_data.exclude_google_ads_videos(data['data'])

        dates = yt_data.get_date_list(watched_videos)
        date_range = max(dates) - min(dates)
        c['date_first'] = min(dates)
        c['date_last'] = max(dates)
        c['dates_plot'] = yt_plots.get_timeseries_plot(dates)
        c['weekday_use_plot'] = yt_plots.get_weekday_use_plot(dates)
        c['hours_plot'] = yt_plots.get_day_usetime_plot(dates)

        n_videos_total = len(watched_videos)
        c['n_videos_total'] = n_videos_total
        c['n_videos_mean']: round((n_videos_total / date_range.days), 2)

        video_titles = yt_data.get_video_title_dict(watched_videos)
        fav_video = yt_data.get_most_watched_video(watched_videos)
        fav_video['title'] = video_titles.get(fav_video['id'])
        c['fav_video'] = fav_video

        channels = yt_data.get_channels_from_history(watched_videos)
        c['n_distinct_channels'] = len(set(channels))
        c['channel_plot'] = yt_plots.get_channel_plot(channels)
        return c

    def get_search_context(self, data):
        c = {}  # c = context
        if data is None:
            c['search_available'] = False
            return c

        c['search_available'] = True
        searches = yt_data.exclude_google_ads_videos(data['data'])

        search_dates = yt_data.get_date_list(searches)
        search_terms = yt_data.get_search_term_frequency(searches, 15)

        c['date_first_search'] = min(search_dates)
        c['n_searches'] = len(searches)
        c['searches'] = search_terms
        c['search_plot'] = yt_plots.get_searches_plot(searches)
        return c
