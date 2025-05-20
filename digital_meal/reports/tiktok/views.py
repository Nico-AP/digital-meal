import time
from datetime import timedelta

import pandas as pd
from django.utils import timezone
from django.views.generic import TemplateView

from digital_meal.reports.tiktok import data_utils
from digital_meal.reports.tiktok.example_data import generate_synthetic_watch_history
from digital_meal.reports.utils_shared import plot_utils
from digital_meal.reports.utils_shared import data_utils as shared_data_utils
from digital_meal.reports.views import BaseReportClassroom, BaseReportIndividual
from digital_meal.tool.models import Classroom


BLUEPRINT_NAMES = {
    'WATCH_HISTORY': 'Angesehene Videos'
}


class TikTokBaseReport:
    """
    Implements shared methods for the generation of TikTok reports.
    """

    @staticmethod
    def add_wh_timeseries_plots_to_context(context, date_list,
                                           min_date, max_date):
        """ Add watch history timeseries plots to the context. """
        dates_days = shared_data_utils.get_summary_counts_per_date(
            date_list, 'd', 'mean')
        dates_plot_days = plot_utils.get_timeseries_plot(
            pd.Series(dates_days),
            date_min=min_date,
            date_max=max_date
        )

        dates_weeks = shared_data_utils.get_summary_counts_per_date(
            date_list, 'w', 'mean')
        dates_plot_weeks = plot_utils.get_timeseries_plot(
            pd.Series(dates_weeks), bin_width=7,
            date_min=min_date, date_max=max_date)

        dates_months = shared_data_utils.get_summary_counts_per_date(
            date_list, 'm', 'mean')
        dates_plot_months = plot_utils.get_timeseries_plot(
            pd.Series(dates_months), bin_width=30,
            date_min=min_date, date_max=max_date)

        dates_years = shared_data_utils.get_summary_counts_per_date(
            date_list, 'y', 'mean')
        dates_plot_years = plot_utils.get_timeseries_plot(
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
    def add_favorite_videos_to_context(context, video_ids):
        """Add the 10 videos to the context that were watched most often."""
        most_popular_vids = pd.Series(video_ids).value_counts()[:10].to_dict()
        vids_top_ten = []
        for key, value in most_popular_vids.items():
            metadata = data_utils.get_video_metadata(key)
            time.sleep(0.1)
            vids_top_ten.append({
                'id': key,
                'count': value,
                'thumbnail': metadata['thumbnail'],
                'channel': metadata['channel']
            })
        context['fav_vids_top_ten'] = vids_top_ten
        return context

    def add_wh_statistics_to_context(self, context, watch_history,
                                     video_ids, n_donations=1, example=False):
        """Add watch history statistics to the context."""
        n_vids_per_day = len(watch_history) / context['dates']['wh_date_range'].days

        # Add overall statistics.
        context.setdefault('watch_stats', {}).update({
            'n_vids_overall': len(watch_history),
            'n_vids_unique_overall': len(set(video_ids)),
            'n_vids_mean_overall': len(watch_history) / n_donations,
            'n_vids_per_day': round(n_vids_per_day, 2)
        })

        # Add interval statistics
        if not example:
            interval_min, interval_max = self.classroom.get_reference_interval()
        else:
            interval_min, interval_max = timezone.now() - timedelta(days=30), timezone.now()

        if interval_min is None and interval_max is None:
            return context

        interval_length = (interval_max - interval_min).days
        wh_interval = shared_data_utils.get_entries_in_date_range(
            watch_history, interval_min, interval_max, 'Date')
        wh_interval_ids = data_utils.get_video_ids(wh_interval)

        context.setdefault('watch_stats', {}).update({
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
            'weekday_use_plot': plot_utils.get_weekday_use_plot(date_list),
            'hours_plot': plot_utils.get_day_usetime_plot(date_list)
        })
        return context


class TikTokReportIndividual(BaseReportIndividual, TikTokBaseReport):
    """Base class to generate an individual report for the YouTube data."""
    template_name = 'reports/tiktok/individual_report.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        donated_data = self.get_donations()

        wh_data = donated_data.get(BLUEPRINT_NAMES['WATCH_HISTORY'])
        if wh_data is not None:
            context.update(self.get_watch_context(wh_data['data']))

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
        watch_history = data
        watched_video_ids = data_utils.get_video_ids(watch_history)
        watched_video_dates = data_utils.get_date_list(watch_history)

        # Add video-related plots and statistics to the context.
        self.add_wh_date_infos_to_context(context, watched_video_dates)
        self.add_wh_statistics_to_context(
            context, watch_history, watched_video_ids)
        self.add_favorite_videos_to_context(
            context, watched_video_ids)
        self.add_wh_timeseries_plots_to_context(
            context, [watched_video_dates],
            context['dates']['wh_dates_min'], context['dates']['wh_dates_max'])
        self.add_wh_heatmap_plots_to_context(context, watched_video_dates)
        return context


class TikTokReportClassroom(BaseReportClassroom, TikTokBaseReport):
    """Generates the classroom report for the YouTube data."""
    model = Classroom
    template_name = 'reports/tiktok/class_report.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        donated_data = self.get_donations()

        if all(v is None for k, v in donated_data.items()):
            self.template_name = 'reports/report_exception.html'
            context['exception_message'] = (
                'Es haben weniger als 5 Personen aus der Klasse ihre Daten '
                'hochgeladen.'
            )
            return context

        # Watch history (wh).
        watch_history_data = donated_data.get(BLUEPRINT_NAMES['WATCH_HISTORY'])
        if watch_history_data is not None:
            context.update(self.get_watch_context(watch_history_data))

        n_donations = [
            len(v) for k, v in donated_data.items()
            if v is not None
        ]
        context['n_participants'] = max(n_donations)
        return context

    def get_watch_context(self, data):
        """Add watch history related statistics and plots to the context."""
        # optimize the times these statistics are computed.
        context = {}
        if data is None:
            context['wh_available'] = False
            return context
        context['wh_available'] = True

        n_donations = len(data)

        # Combine the watch histories of all individuals in one list.
        wh_combined = []
        whs_individual = [e['data'] for e in data]
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
        # by the most individuals.
        wh_combined_ids_sets = []
        for wh in whs_individual:
            wh_ids = data_utils.get_video_ids(wh)
            wh_combined_ids_sets += list(set(wh_ids))
        self.add_favorite_videos_to_context(
            context, wh_combined_ids_sets)

        # Create a list of lists of wh dates of each individual. Used to
        # create the aggregated timeseries plot and the aggregated heatmap.
        whs_individual_dates = [
            data_utils.get_date_list(wh) for wh in whs_individual]
        self.add_wh_timeseries_plots_to_context(
            context, whs_individual_dates,
            context['dates']['wh_dates_min'], context['dates']['wh_dates_max'])
        self.add_wh_heatmap_plots_to_context(context, wh_combined_dates)
        return context


class TikTokExampleReport(TikTokBaseReport, TemplateView):
    template_name = 'reports/tiktok/example_report.html'

    def get_data(self):
        """ Generate synthetic data for example report. """
        return

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Generate synthetic data.
        start_date = timezone.now().date() - timedelta(days=5)
        wh_data = generate_synthetic_watch_history(start_date)

        # Add watch history (wh) data to context.
        context.update(self.get_watch_context(wh_data['data']))
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
        watch_history = data
        watched_video_ids = data_utils.get_video_ids(watch_history)
        watched_video_dates = data_utils.get_date_list(watch_history)

        # Add video-related plots and statistics to the context.
        self.add_wh_date_infos_to_context(context, watched_video_dates)
        self.add_wh_statistics_to_context(
            context, watch_history, watched_video_ids, example=True)
        self.add_favorite_videos_to_context(
            context, watched_video_ids)
        self.add_wh_timeseries_plots_to_context(
            context, [watched_video_dates],
            context['dates']['wh_dates_min'], context['dates']['wh_dates_max'])
        self.add_wh_heatmap_plots_to_context(context, watched_video_dates)
        return context
