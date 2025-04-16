from datetime import datetime, timedelta

import pandas as pd
from django.utils import timezone
from django.views.generic import TemplateView

from digital_meal.reports.youtube import data_utils
from digital_meal.reports.youtube import plot_utils
from digital_meal.reports.youtube.example_data import (
    generate_synthetic_watch_history, generate_synthetic_search_history)
from digital_meal.reports.utils_shared import plot_utils as shared_plot_utils
from digital_meal.reports.utils_shared import data_utils as shared_data_utils
from digital_meal.reports.views import BaseReportClassroom, BaseReportIndividual
from digital_meal.tool.models import Classroom


class YouTubeBaseReport:
    """
    Implements shared methods for the generation of YouTube reports.
    """

    @staticmethod
    def add_wh_timeseries_plots_to_context(context, date_list,
                                           min_date, max_date):
        """ Add watch history timeseries plots to the context. """
        dates_days = shared_data_utils.get_summary_counts_per_date(
            date_list, 'd', 'mean')
        dates_plot_days = shared_plot_utils.get_timeseries_plot(
            pd.Series(dates_days),
            date_min=min_date,
            date_max=max_date
        )

        dates_weeks = shared_data_utils.get_summary_counts_per_date(
            date_list, 'w', 'mean')
        dates_plot_weeks = shared_plot_utils.get_timeseries_plot(
            pd.Series(dates_weeks), bin_width=7,
            date_min=min_date, date_max=max_date)

        dates_months = shared_data_utils.get_summary_counts_per_date(
            date_list, 'm', 'mean')
        dates_plot_months = shared_plot_utils.get_timeseries_plot(
            pd.Series(dates_months), bin_width=30,
            date_min=min_date, date_max=max_date)

        dates_years = shared_data_utils.get_summary_counts_per_date(
            date_list, 'y', 'mean')
        dates_plot_years = shared_plot_utils.get_timeseries_plot(
            pd.Series(dates_years), bin_width=365,
            date_min=min_date, date_max=max_date)

        context.update({
            'dates_plot_days': dates_plot_days,
            'dates_plot_weeks': dates_plot_weeks,
            'dates_plot_months': dates_plot_months,
            'dates_plot_years': dates_plot_years
        })
        return context

    @staticmethod
    def add_wh_date_infos_to_context(context, date_list):
        """ Add watch history date information to the context. """
        context.update({
            'dates': {
                'wh_dates_min': min(date_list),
                'wh_dates_max': max(date_list),
                'wh_date_range': max(date_list) - min(date_list)
            }
        })
        return context

    @staticmethod
    def add_favorite_videos_to_context(context, watch_history, video_ids):
        """Add the 10 videos to the context that were watched most often."""
        video_titles = data_utils.get_video_title_dict(watch_history)
        most_popular_vids = pd.Series(video_ids).value_counts()[:10].to_dict()
        vids_top_ten = []
        for key, value in most_popular_vids.items():
            vids_top_ten.append({
                'id': key,
                'count': value,
                'title': data_utils.clean_video_title(video_titles.get(key))
            })
        context['fav_vids_top_ten'] = vids_top_ten
        return context

    def add_wh_statistics_to_context(self, context, watch_history,
                                     video_ids, n_donations=1, example=False):
        """Add watch history statistics to the context."""
        n_vids_per_day = len(watch_history) / context['dates']['wh_date_range'].days

        if not example:
            interval_min, interval_max = self.classroom.get_reference_interval()
        else:
            interval_min, interval_max = datetime.now() - timedelta(days=30), datetime.now()

        interval_length = (interval_max - interval_min).days
        wh_interval = shared_data_utils.get_entries_in_date_range(
            watch_history, interval_min, interval_max)
        wh_interval_ids = data_utils.get_video_ids(wh_interval)

        context.setdefault('watch_stats', {}).update({
            # Statistics overall
            'n_vids_overall': len(watch_history),
            'n_vids_unique_overall': len(set(video_ids)),
            'n_vids_mean_overall': len(watch_history) / n_donations,
            'n_vids_per_day': round(n_vids_per_day, 2),
            # Statistics interval
            'n_vids_interval': len(wh_interval),
            'n_vids_unique_interval': len(set(wh_interval_ids)),
            'n_vids_mean_interval': len(wh_interval) / n_donations,
            'n_vids_per_interval': len(wh_interval_ids) / interval_length,
        })

        context.setdefault('dates', {}).update({
            'wh_int_min_date': interval_min,
            'wh_int_max_date': interval_max,
        })
        return context

    @staticmethod
    def add_wh_heatmap_plots_to_context(context, date_list):
        """Add watch history heatmap plots to the context."""
        context.update({
            'weekday_use_plot': shared_plot_utils.get_weekday_use_plot(date_list),
            'hours_plot': shared_plot_utils.get_day_usetime_plot(date_list)
        })
        return context

    @staticmethod
    def add_wh_channel_info_to_context(context, channels,
                                       channels_for_plot=None):
        """Add watch history channel information to the context."""
        if channels_for_plot is None:
            channels_for_plot = channels
        context.update({
            'channel_plot': plot_utils.get_channel_plot(channels_for_plot),
            'n_distinct_channels': len(set(channels))
        })
        return context

    def add_sh_statistics_to_context(self, context,
                                     search_history, n_donations=1, example=False):
        """Add search history statistics to the context."""
        if not example:
            interval_min, interval_max = self.classroom.get_reference_interval()
        else:
            interval_min, interval_max = datetime.now() - timedelta(days=30), datetime.now()

        sh_interval = shared_data_utils.get_entries_in_date_range(
            search_history, interval_min, interval_max)
        context.update({
            # Statistics overall.
            'n_searches_overall': len(search_history),
            'n_searches_mean_overall': len(search_history) / n_donations,
            # Statistics interval
            'sh_int_min_date': interval_min,
            'sh_int_max_date': interval_max,
            'n_search_interval': len(sh_interval),
            'n_search_mean_interval': len(sh_interval) / n_donations
        })
        return context

    @staticmethod
    def add_sh_plot_to_context(context, search_terms):
        """Add search history plot to the context."""
        context['search_plot'] = plot_utils.get_searches_plot(search_terms)
        return context


class YouTubeReportIndividual(BaseReportIndividual, YouTubeBaseReport):
    """Base class to generate an individual report for the YouTube data."""
    template_name = 'reports/youtube/individual_report.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        data = self.get_data()

        # TODO: Add checks for data availability.
        # Add watch history (wh) data to context.
        wh_data = data['donations'].get('Angesehene Videos')
        if wh_data is not None:
            context.update(self.get_watch_context(wh_data['data']))

        # TODO: Add checks for data availability.
        # Add search history (sh) data to context.
        sh_data = data['donations'].get('Suchverlauf')
        if sh_data is not None:
            context.update(self.get_search_context(sh_data))

        return context

    def get_watch_context(self, data):
        """Add watch history related statistics and plots to the context."""
        context = {}
        if data is None:
            context['wh_available'] = False
            return context
        context['wh_available'] = True

        # Create list of watched videos and separate lists for ids and dates
        # of watched videos.
        wh = data_utils.exclude_google_ads_videos(data)
        wh_ids = data_utils.get_video_ids(wh)
        wh_dates = data_utils.get_date_list(wh)

        # Add video-related plots and statistics to the context.
        self.add_wh_date_infos_to_context(context, wh_dates)
        self.add_wh_statistics_to_context(context, wh, wh_ids)
        self.add_favorite_videos_to_context(context, wh, wh_ids)
        self.add_wh_timeseries_plots_to_context(
            context, [wh_dates],
            context['dates']['wh_dates_min'], context['dates']['wh_dates_max'])
        self.add_wh_heatmap_plots_to_context(context, wh_dates)

        # Add channel-releated information to the context.
        channels = data_utils.get_channels_from_history(wh)
        self.add_wh_channel_info_to_context(context, channels)
        return context

    def get_search_context(self, data):
        """Add search history related statistics and plots to the context."""
        context = {}
        if data is None:
            context['search_available'] = False
            return context
        context['search_available'] = True

        sh = data_utils.exclude_ads_from_search_history(data)
        sh = data_utils.clean_search_titles(sh)
        search_terms = [t['title'] for t in sh]

        self.add_sh_statistics_to_context(context, sh)
        self.add_sh_plot_to_context(context, search_terms)
        return context


class YouTubeReportClassroom(BaseReportClassroom, YouTubeBaseReport):
    """Generates the classroom report for the YouTube data."""
    model = Classroom
    template_name = 'reports/youtube/class_report.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        data = self.get_data()

        # TODO: Add checks for data availability.

        if all(v is None for k, v in data['donations'].items()):
            self.template_name = 'reports/report_exception.html'
            context['exception_message'] = (
                'Es haben weniger als 5 Personen aus der Klasse ihre Daten '
                'hochgeladen.'
            )
            return context

        # Watch history (wh).
        watch_history_id = 'Angesehene Videos'
        if watch_history_id in data['donations'].keys():
            watch_history_data = data['donations'][watch_history_id]
            context.update(self.get_watch_context(watch_history_data))

        # Search history (sh).
        search_history_id = 'Suchverlauf'
        if search_history_id in data['donations'].keys():
            search_history_data = data['donations'][search_history_id]
            context.update(self.get_search_context(search_history_data))

        # Subscribed channels (sc).
        subscription_id = 'Abonnierte Kanäle'
        if subscription_id in data['donations'].keys():
            subscription_data = data['donations'][subscription_id]
            context.update(self.get_subscription_context(subscription_data))

        n_donations = [
            len(v) for k, v in data['donations'].items()
            if v is not None
        ]
        context['n_participants'] = max(n_donations)
        return context

    def get_watch_context(self, data):
        """Add watch history related statistics and plots to the context."""
        # TODO: Move this to the class level ->
        # optimize the times these statistics are computed.
        context = {}
        if data is None:
            context['wh_available'] = False
            return context
        context['wh_available'] = True

        n_donations = len(data)

        # Combine the watch histories of all individuals in one list.
        wh_combined = []
        whs_individual = [
            data_utils.exclude_google_ads_videos(e['data'])
            for e in data
        ]
        for wh in whs_individual:
            wh_combined += wh

        # Get separate lists for the video ids and the dates.
        wh_combined_ids = data_utils.get_video_ids(wh_combined)
        wh_combined_dates = data_utils.get_date_list(wh_combined)

        # Add wh date information and wh statistics to the context.
        self.add_wh_date_infos_to_context(context,  wh_combined_dates)
        self.add_wh_statistics_to_context(
            context, wh_combined, wh_combined_ids, n_donations)

        # Create a list of the sets of video ids for each individual.
        # Used to determine which videos have been watched at least once
        # by the most invidiuals.
        wh_combined_ids_sets = []
        for wh in whs_individual:
            wh_ids = data_utils.get_video_ids(wh)
            wh_combined_ids_sets += list(set(wh_ids))
        self.add_favorite_videos_to_context(
            context, wh_combined, wh_combined_ids_sets)

        # Create a list of lists of wh dates of each individual. Used to
        # create the aggregated timeseries plot and the aggregated heatmap.
        whs_individual_dates = [
            data_utils.get_date_list(wh) for wh in whs_individual]
        self.add_wh_timeseries_plots_to_context(
            context, whs_individual_dates,
            context['dates']['wh_dates_min'], context['dates']['wh_dates_max'])
        self.add_wh_heatmap_plots_to_context(context, wh_combined_dates)

        # Get the channels that have been watched by at least 2 people in
        # the class to add the channel plot to the context.
        channel_sets = []
        for wh in whs_individual:
            channel_sets += list(set(data_utils.get_channels_from_history(wh)))
        channel_counts = pd.Series(channel_sets).value_counts()
        allowed_channels = channel_counts[channel_counts > 1].index.tolist()
        combined_channels = data_utils.get_channels_from_history(wh_combined)
        channels_for_plot = [
            c for c in combined_channels
            if c in allowed_channels
        ]
        self.add_wh_channel_info_to_context(
            context, combined_channels, channels_for_plot)
        return context

    def get_search_context(self, data):
        """Add search history related statistics and plots to the context."""
        context = {}
        if data is None:
            context['sh_available'] = False
            return context
        context['sh_available'] = True

        n_donations = len(data)

        # Remove Google Ads from search histories and combine the histories of
        # all individuals in one list.
        sh_combined = []
        shs_individual = []
        for entry in data:
            entry = data_utils.exclude_ads_from_search_history(entry['data'])
            cleaned_entry = data_utils.clean_search_titles(entry)
            sh_combined += cleaned_entry
            shs_individual.append(cleaned_entry)

        self.add_sh_statistics_to_context(context, sh_combined, n_donations)

        # Get the search terms that have been used by at least 2 people in
        # the class to add the search term plot to the context.
        terms_combined = [t['title'] for t in sh_combined]
        terms_individual = [[t['title'] for t in sh] for sh in shs_individual]
        sh_sets = []
        for sh in terms_individual:
            sh_sets += list(set(sh))
        sh_vc = pd.Series(sh_sets).value_counts()
        allowed_terms = sh_vc[sh_vc > 1].index.tolist()
        terms_for_plot = [t for t in terms_combined if t in allowed_terms]
        self.add_sh_plot_to_context(context, terms_for_plot)

        return context

    def get_subscription_context(self, data):
        """Add subscription related statistics and plots to the context."""
        def clean_channel_list(channel_list):
            """
            Cleans and standardizes a list of channel dictionaries by
            renaming keys.

            Args:
                channel_list (list): A list of dictionaries, each
                representing a channel.

            Returns:
                list: A new list of dictionaries with standardized keys.
            """
            ddm_id_key = 'Channel ID|Kanal-ID|ID des cha.*|ID canale'
            ddm_title_key = (
                'Channel title|Kanaltitel|Titres des cha.*|Titolo canale'
            )
            keys = {
                f'{ddm_id_key}': 'id',
                f'{ddm_title_key}': 'title',
            }
            channels = []
            for channel in channel_list:
                for key, value in keys.items():
                    channel[value] = channel.pop(key, None)
                channels.append(channel)
            return channels

        context = {}
        if data is None:
            context['sc_available'] = False
            return context
        context['sc_available'] = True

        n_donations = len(data)

        # Combine the subscription data of all individuals in one list.
        sc_combined = []
        for entry in data:
            sc_combined += entry['data']
        sc_combined = clean_channel_list(sc_combined)

        # Add basic subscription statistics to the context.
        context.setdefault('sub_stats', {}).update({
            'n_subs': len(sc_combined),
            'n_subs_mean': len(sc_combined) / n_donations
        })

        # Compute statistics about channel prevalence in the class.
        sc_titles = [entry['title'] for entry in sc_combined]
        subs_counts = pd.Series(sc_titles).value_counts()
        n_subs_multiple = subs_counts[subs_counts > 1]
        context.setdefault('sub_stats', {}).update({
            'n_subs_unique': len(set(sc_titles)),
            'n_subs_multiple': len(n_subs_multiple),
            'most_popular_channels': subs_counts.nlargest(10).to_dict()
        })
        return context


class YouTubeExampleReport(YouTubeBaseReport, TemplateView):
    template_name = 'reports/youtube/example_report.html'

    def get_data(self):
        """ Generate synthetic data for example report. """
        return

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Generate synthetic data.
        start_date = timezone.now().date() - timedelta(days=5)
        wh_data = generate_synthetic_watch_history(start_date)
        sh_data = generate_synthetic_search_history(start_date)

        # Add watch history (wh) data to context.
        context.update(self.get_watch_context(wh_data['data']))

        # Add search history (sh) data to context.
        context.update(self.get_search_context(sh_data['data']))

        return context

    def get_watch_context(self, data):
        """Add watch history related statistics and plots to the context."""
        context = {}
        if data is None:
            context['wh_available'] = False
            return context
        context['wh_available'] = True

        # Create list of watched videos and separate lists for ids and dates
        # of watched videos.
        wh = data_utils.exclude_google_ads_videos(data)
        wh_ids = data_utils.get_video_ids(wh)
        wh_dates = data_utils.get_date_list(wh)

        # Add video-related plots and statistics to the context.
        self.add_wh_date_infos_to_context(context, wh_dates)
        self.add_wh_statistics_to_context(context, wh, wh_ids, example=True)
        self.add_favorite_videos_to_context(context, wh, wh_ids)
        self.add_wh_timeseries_plots_to_context(
            context, [wh_dates],
            context['dates']['wh_dates_min'], context['dates']['wh_dates_max'])
        self.add_wh_heatmap_plots_to_context(context, wh_dates)

        # Add channel-releated information to the context.
        channels = data_utils.get_channels_from_history(wh)
        self.add_wh_channel_info_to_context(context, channels)
        return context

    def get_search_context(self, data):
        """Add search history related statistics and plots to the context."""
        context = {}
        if data is None:
            context['search_available'] = False
            return context
        context['search_available'] = True

        sh = data_utils.exclude_ads_from_search_history(data)
        sh = data_utils.clean_search_titles(sh)
        search_terms = [t['title'] for t in sh]

        self.add_sh_statistics_to_context(context, sh, example=True)
        self.add_sh_plot_to_context(context, search_terms)
        return context
