import datetime
import json
import pandas as pd
import requests

from django.urls import reverse_lazy
from django.views.generic import DetailView

from ..models import Classroom
from ..utils import yt_data, yt_plots


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
        return self.object.track.data_endpoint

    def get_token(self):
        return self.object.track.ddm_api_token

    def get_payload(self):
        return {'class': self.object.class_id, }

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
        print(f'Classroom report Requested: {datetime.datetime.now()}')
        context = super().get_context_data(**kwargs)
        data = json.loads(self.get_data())

        print(f'Received class data from API: {datetime.datetime.now()}')

        if all(v is None for k, v in data['donations'].items()):
            self.template_name = 'digital_meal/reports/report_exception.html'
            context['exception_message'] = (
                'Es haben weniger als 5 Personen aus der Klasse ihre Daten '
                'hochgeladen.'
            )
            return context

        # Watch history (wh)
        print(f'Started to generate Watch History Report: {datetime.datetime.now()}')
        context.update(self.get_watch_context(data['donations']['Angesehene Videos']))

        # Search history (sh)
        print(f'Started to generate Search History Report: {datetime.datetime.now()}')
        context.update(self.get_search_context(data['donations']['Suchverlauf']))

        # Subscribed channels (sc)
        print(f'Started to generate Subscription Report: {datetime.datetime.now()}')
        context.update(self.get_subs_context(data['donations']['Subs 2']))

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

        whs_individual = [yt_data.exclude_google_ads_videos(e['data']) for e in data]
        wh_combined = []
        for wh in whs_individual:
            wh_combined += wh

        wh_combined_ids = yt_data.get_video_ids(wh_combined)
        c['n_vids_overall'] = len(wh_combined)
        c['n_vids_unique_overall'] = len(set(wh_combined_ids))
        c['n_vids_mean_overall'] = len(wh_combined) / n_donations

        interval_min, interval_max = self.object.get_reference_interval()
        c['wh_int_min_date'] = interval_min
        c['wh_int_max_date'] = interval_max
        wh_interval = yt_data.get_entries_in_date_range(wh_combined, interval_min, interval_max)

        wh_interval_ids = yt_data.get_video_ids(wh_interval)
        c['n_vids_interval'] = len(wh_interval)
        c['n_vids_unique_interval'] = len(set(wh_interval_ids))
        c['n_vids_mean_interval'] = len(wh_interval) / n_donations

        # Barplot "n videos over time" - y: n_videos, x: dates
        whs_individual_dates = [yt_data.get_date_list(wh) for wh in whs_individual]
        wh_combined_dates = yt_data.get_date_list(wh_combined)
        min_date = min(wh_combined_dates)
        max_date = max(wh_combined_dates)

        dates_days = yt_data.get_summary_counts_per_date(whs_individual_dates, 'd', 'median')
        c['dates_plot_days'] = yt_plots.get_timeseries_plot(
            pd.Series(dates_days), date_min=min_date, date_max=max_date)

        dates_weeks = yt_data.get_summary_counts_per_date(whs_individual_dates, 'w', 'median')
        c['dates_plot_weeks'] = yt_plots.get_timeseries_plot(
            pd.Series(dates_weeks), bin_width=7, date_min=min_date, date_max=max_date)

        dates_months = yt_data.get_summary_counts_per_date(whs_individual_dates, 'w', 'median')
        c['dates_plot_months'] = yt_plots.get_timeseries_plot(
            pd.Series(dates_months), bin_width=30, date_min=min_date, date_max=max_date)

        dates_years = yt_data.get_summary_counts_per_date(whs_individual_dates, 'y', 'median')
        c['dates_plot_years'] = yt_plots.get_timeseries_plot(
            pd.Series(dates_years), bin_width=365, date_min=min_date, date_max=max_date)

        c['wh_dates_min'] = min_date
        c['wh_dates_max'] = max_date

        # Barplot "n videos per weekday" - y: n_videos, x: weekdays
        c['weekday_use_plot'] = yt_plots.get_weekday_use_plot(wh_combined_dates)

        # Heatmap "n videos per day per hour"
        c['hours_plot'] = yt_plots.get_day_usetime_plot(wh_combined_dates)
        return c

    def get_search_context(self, data):
        c = {}  # c = context
        if data is None:
            c['sh_available'] = False
            return c

        c['sh_available'] = True
        n_donations = len(data)

        sh_combined = []
        for entry in data:
            sh_combined += entry['data']

        sh_combined = yt_data.exclude_ads_from_search_history(sh_combined)
        sh_combined = yt_data.clean_search_titles(sh_combined)
        sh_combined_ids = yt_data.get_video_ids(sh_combined)
        c['n_searches_overall'] = len(sh_combined)
        c['n_searches_unique_overall'] = len(set(sh_combined_ids))
        c['n_searches_mean_overall'] = len(sh_combined) / n_donations

        interval_min, interval_max = self.object.get_reference_interval()
        c['sh_int_min_date'] = interval_min
        c['sh_int_max_date'] = interval_max
        sh_interval = yt_data.get_entries_in_date_range(sh_combined, interval_min, interval_max)

        sh_interval_ids = yt_data.get_video_ids(sh_interval)
        c['n_search_interval'] = len(sh_interval)
        c['n_search_unique_interval'] = len(set(sh_interval_ids))
        c['n_search_mean_interval'] = len(sh_interval) / n_donations

        c['search_plot'] = yt_plots.get_searches_plot(sh_combined)
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

        sc_combined = []
        for entry in data:
            sc_combined += entry['data']

        sc_combined = clean_channel_list(sc_combined)
        sc_titles = [entry['title'] for entry in sc_combined]

        c['n_subs'] = len(sc_combined)
        c['n_subs_unique'] = len(set(sc_titles))
        c['n_subs_mean'] = len(sc_combined) / n_donations

        subs_counts = pd.Series(sc_titles).value_counts()
        # subs_counts_relative = pd.Series(sc_titles).value_counts(normalize=True)
        n_subs_multiple = subs_counts[subs_counts > 1]
        c['n_subs_multiple'] = len(n_subs_multiple)
        c['most_popular_channels'] = subs_counts.nlargest(50).to_dict()
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

        # These are the names of the ddm-blueprint.
        watch_history_id = 'Angesehene Videos'
        search_history_id = 'Suchverlauf'

        # Watch history
        if watch_history_id in data['donations'].keys():
            context.update(self.get_watch_context(data['donations'][watch_history_id]))

        # Search history (sh)
        if search_history_id in data['donations'].keys():
            context.update(self.get_search_context(data['donations'][search_history_id]))

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
