import datetime
import json
from smtplib import SMTPException

import pandas as pd
import requests
from django.core.mail import send_mail
from django.http import JsonResponse

from django.urls import reverse_lazy
from django.views import View
from django.views.generic import DetailView

from ..tool.models import Classroom
from .utils import yt_data, yt_plots


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
    template_name = 'reports/youtube/class_report.html'

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


class BaseIndividualReport(DDMReport, DetailView):
    """ Base class to generate an individual report. """
    model = Classroom
    template_name = 'reports/youtube/individual_report.html'

    def setup(self, request, *args, **kwargs):
        return super().setup(request, *args, **kwargs)

    def get_endpoint(self):
        return self.object.track.ddm_api_endpoint

    def get_token(self):
        return self.object.track.ddm_api_token

    def get_payload(self):
        payload = {'participant_id': self.kwargs.get('participant_id')}
        return payload


class BaseYouTubeReport:

    @staticmethod
    def add_wh_timeseries_plots_to_context(context, date_list, min_date, max_date):
        dates_days = yt_data.get_summary_counts_per_date(date_list, 'd', 'mean')
        context['dates_plot_days'] = yt_plots.get_timeseries_plot(
            pd.Series(dates_days), date_min=min_date, date_max=max_date)

        dates_weeks = yt_data.get_summary_counts_per_date(date_list, 'w', 'mean')
        context['dates_plot_weeks'] = yt_plots.get_timeseries_plot(
            pd.Series(dates_weeks), bin_width=7, date_min=min_date, date_max=max_date)

        dates_months = yt_data.get_summary_counts_per_date(date_list, 'w', 'mean')
        context['dates_plot_months'] = yt_plots.get_timeseries_plot(
            pd.Series(dates_months), bin_width=30, date_min=min_date, date_max=max_date)

        dates_years = yt_data.get_summary_counts_per_date(date_list, 'y', 'mean')
        context['dates_plot_years'] = yt_plots.get_timeseries_plot(
            pd.Series(dates_years), bin_width=365, date_min=min_date, date_max=max_date)
        return context

    @staticmethod
    def add_wh_date_infos_to_context(context, date_list):
        context['wh_dates_min'] = min(date_list)
        context['wh_dates_max'] = max(date_list)
        context['wh_date_range'] = max(date_list) - min(date_list)
        return context

    @staticmethod
    def add_favorite_videos_to_context(context, watch_history, video_ids):
        video_titles = yt_data.get_video_title_dict(watch_history)
        most_popular_videos = pd.Series(video_ids).value_counts()[:10].to_dict()
        videos_top_ten = []
        for key, value in most_popular_videos.items():
            videos_top_ten.append({
                'id': key,
                'count': value,
                'title': yt_data.clean_video_title(video_titles.get(key))
            })
        context['fav_vids_top_ten'] = videos_top_ten
        return context

    def add_wh_statistics_to_context(self, context, watch_history, video_ids, n_donations=1, ):
        # Statistics overall
        context['n_vids_overall'] = len(watch_history)
        context['n_vids_unique_overall'] = len(set(video_ids))
        context['n_vids_mean_overall'] = len(watch_history) / n_donations
        context['n_vids_per_day']: round((len(watch_history) / context['wh_date_range'].days), 2)

        # Statistics interval
        interval_min, interval_max = self.object.get_reference_interval()
        context['wh_int_min_date'] = interval_min
        context['wh_int_max_date'] = interval_max
        wh_interval = yt_data.get_entries_in_date_range(
            watch_history, interval_min, interval_max)
        wh_interval_ids = yt_data.get_video_ids(wh_interval)
        context['n_vids_interval'] = len(wh_interval)
        context['n_vids_unique_interval'] = len(set(wh_interval_ids))
        context['n_vids_mean_interval'] = len(wh_interval) / n_donations
        return context

    @staticmethod
    def add_wh_plots_to_context(context, date_list):
        context['weekday_use_plot'] = yt_plots.get_weekday_use_plot(date_list)
        context['hours_plot'] = yt_plots.get_day_usetime_plot(date_list)
        return context

    @staticmethod
    def add_wh_channel_info_to_context(context, channels, channels_for_plot=None):
        if channels_for_plot is None:
            channels_for_plot = channels
        context['channel_plot'] = yt_plots.get_channel_plot(channels_for_plot)
        context['n_distinct_channels'] = len(set(channels))
        return context

    def add_sh_statistics_to_context(self, context, search_history, n_donations=1):
        # Statistics overall
        context['n_searches_overall'] = len(search_history)
        context['n_searches_mean_overall'] = len(search_history) / n_donations

        # Statistics interval
        interval_min, interval_max = self.object.get_reference_interval()
        context['sh_int_min_date'] = interval_min
        context['sh_int_max_date'] = interval_max
        sh_interval = yt_data.get_entries_in_date_range(search_history, interval_min, interval_max)
        context['n_search_interval'] = len(sh_interval)
        context['n_search_mean_interval'] = len(sh_interval) / n_donations
        return context

    @staticmethod
    def add_sh_plot_to_context(context, search_terms):
        context['search_plot'] = yt_plots.get_searches_plot(search_terms)
        return context


class ClassroomReportYouTube(BaseClassroomReport, BaseYouTubeReport):
    """ Classroom report for the YouTube data. """
    model = Classroom
    template_name = 'reports/youtube/class_report.html'

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
        watch_history_id = 'Angesehene Videos'
        if watch_history_id in data['donations'].keys():
            context.update(self.get_watch_context(data['donations'][watch_history_id]))

        # Search history (sh)
        print(f'Started to generate Search History Report: {datetime.datetime.now()}')
        search_history_id = 'Suchverlauf'
        if search_history_id in data['donations'].keys():
            context.update(self.get_search_context(data['donations'][search_history_id]))

        # Subscribed channels (sc)
        print(f'Started to generate Subscription Report: {datetime.datetime.now()}')
        subscription_id = 'Abonnierte Kanäle'
        if subscription_id in data['donations'].keys():
            context.update(self.get_subs_context(data['donations'][subscription_id]))

        n_donations = [len(v) for k, v in data['donations'].items() if v is not None]
        context['n_participants'] = max(n_donations)
        return context

    def get_watch_context(self, data):
        # TODO: Move this to the class level -> optimize the times these statistics are computed.
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
        wh_combined_dates = yt_data.get_date_list(wh_combined)
        self.add_wh_date_infos_to_context(c,  wh_combined_dates)
        self.add_wh_statistics_to_context(c, wh_combined, wh_combined_ids, n_donations)

        wh_combined_ids_sets = []
        for wh in whs_individual:
            wh_ids = yt_data.get_video_ids(wh)
            wh_combined_ids_sets += list(set(wh_ids))
        self.add_favorite_videos_to_context(c, wh_combined, wh_combined_ids_sets)
        whs_individual_dates = [yt_data.get_date_list(wh) for wh in whs_individual]

        self.add_wh_timeseries_plots_to_context(c, whs_individual_dates, c['wh_dates_min'], c['wh_dates_max'])
        self.add_wh_plots_to_context(c, wh_combined_dates)

        channel_sets = []
        for wh in whs_individual:
            channel_sets += list(set(yt_data.get_channels_from_history(wh)))
        channel_vc = pd.Series(channel_sets).value_counts()
        allowed_channels = channel_vc[channel_vc > 1].index.tolist()
        combined_channels = yt_data.get_channels_from_history(wh_combined)
        channels_for_plot = [c for c in combined_channels if c in allowed_channels]
        self.add_wh_channel_info_to_context(c, combined_channels, channels_for_plot)
        return c

    def get_search_context(self, data):
        c = {}  # c = context
        if data is None:
            c['sh_available'] = False
            return c
        c['sh_available'] = True

        n_donations = len(data)
        sh_combined = []
        shs_individual = []
        for entry in data:
            entry = yt_data.exclude_ads_from_search_history(entry['data'])
            cleaned_entry = yt_data.clean_search_titles(entry)
            sh_combined += cleaned_entry
            shs_individual.append(cleaned_entry)

        self.add_sh_statistics_to_context(c, sh_combined, n_donations)

        # For search plot, only use search terms that are used by at least 2 people.
        terms_combined = [t['title'] for t in sh_combined]
        terms_individual = [[t['title'] for t in sh] for sh in shs_individual]

        sh_sets = []
        for sh in terms_individual:
            sh_sets += list(set(sh))
        sh_vc = pd.Series(sh_sets).value_counts()
        allowed_terms = sh_vc[sh_vc > 1].index.tolist()
        terms_for_plot = [t for t in terms_combined if t in allowed_terms]

        self.add_sh_plot_to_context(c, terms_for_plot)
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
        n_subs_multiple = subs_counts[subs_counts > 1]
        c['n_subs_multiple'] = len(n_subs_multiple)
        c['most_popular_channels'] = subs_counts.nlargest(10).to_dict()
        return c


class IndividualReportYouTube(BaseIndividualReport, BaseYouTubeReport):
    """ Base class to generate an individual report for the YouTube data. """
    template_name = 'reports/youtube/individual_report.html'

    def get_endpoint(self):
        kwargs = {'pk': self.object.pk}
        return self.request.build_absolute_uri(reverse_lazy('individual_data_api', kwargs=kwargs))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        data = json.loads(self.get_data())

        # Watch history
        watch_history_id = 'Angesehene Videos'

        # TODO: Add check for no donations available.

        if watch_history_id in data['donations'].keys():
            context.update(self.get_watch_context(data['donations'][watch_history_id]))

        # Search history (sh)
        search_history_id = 'Suchverlauf'
        if search_history_id in data['donations'].keys():
            context.update(self.get_search_context(data['donations'][search_history_id]))

        # Subscribed channels (sc)
        subscription_id = 'Abonnierte Kanäle'
        if subscription_id in data['donations'].keys():
            context.update(self.get_subs_context(data['donations'][subscription_id]))

        return context

    def get_watch_context(self, data):
        c = {}  # c = context
        if data is None:
            c['wh_available'] = False
            return c
        c['wh_available'] = True

        wh = yt_data.exclude_google_ads_videos(data['data'])
        wh_ids = yt_data.get_video_ids(wh)

        wh_dates = yt_data.get_date_list(wh)
        self.add_wh_date_infos_to_context(c, wh_dates)
        self.add_wh_statistics_to_context(c, wh, wh_ids)
        self.add_favorite_videos_to_context(c, wh, wh_ids)
        self.add_wh_timeseries_plots_to_context(c, [wh_dates], c['wh_dates_min'], c['wh_dates_max'])
        self.add_wh_plots_to_context(c, wh_dates)

        # Watched channels
        channels = yt_data.get_channels_from_history(wh)
        self.add_wh_channel_info_to_context(c, channels)
        return c

    def get_search_context(self, data):
        c = {}  # c = context
        if data is None:
            c['search_available'] = False
            return c
        c['search_available'] = True

        sh = yt_data.exclude_google_ads_videos(data['data'])
        self.add_sh_statistics_to_context(c, sh)
        search_terms = [t['title'] for t in sh]

        self.add_sh_plot_to_context(c, search_terms)
        return c


class SendReportLink(View):
    """ Sends the link to the open report to a given e-mail address. """

    def post(self, request, *args, **kwargs):
        email_address = request.POST.get('email', None)
        report_link = request.POST.get('link', None)

        if email_address and report_link:
            try:
                send_mail(
                    subject='Link zum Digital Meal Report',
                    message=f'Link zum Report: {report_link}',
                    from_email='contact@digital-meal.ch',
                    recipient_list=[email_address],
                    fail_silently=False
                )
                return JsonResponse({'status': 'success'})
            except SMTPException:
                return JsonResponse({'status': 'error'})

        else:
            return JsonResponse({'status': 'error'})
