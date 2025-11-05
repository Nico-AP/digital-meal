import time
from collections import Counter
from datetime import datetime, timedelta

import pandas as pd
import requests
from django.utils import timezone
from django.views.generic import TemplateView

from digital_meal.reports.utils_shared.data_utils import normalize_texts
from digital_meal.reports.tiktok import data_utils
from digital_meal.reports.tiktok.example_data import (
    generate_synthetic_watch_history, generate_synthetic_search_history)
from digital_meal.reports.utils_shared import plot_utils as shared_plot_utils
from digital_meal.reports.utils_shared import plot_utils as plot_utils
from digital_meal.reports.utils_shared import data_utils as shared_data_utils
from digital_meal.reports.views import BaseReportClassroom, BaseReportIndividual
from digital_meal.tool.models import Classroom


BLUEPRINT_NAMES = {
    'WATCH_HISTORY': 'Angesehene Videos',
    'SEARCH_HISTORY': 'Durchgeführte Suchen'
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
        min_date = min(date_list)
        max_date = max(date_list)

        context.update({
            'dates': {
                'wh_dates_min': min_date,
                'wh_dates_max': max_date,
                'wh_date_range': max_date - min_date
            }
        })
        return context

    @staticmethod
    def add_favorite_videos_to_context(context, video_ids):
        """Add the 10 videos to the context that were watched most often."""
        most_popular_vids = pd.Series(video_ids).value_counts()[:10]

        with requests.Session() as session:
            vids_top_ten = []
            for key, value in most_popular_vids.items():
                metadata = data_utils.get_video_metadata(key, session)
                time.sleep(0.1)
                vids_top_ten.append({
                    'id': key,
                    'count': value,
                    'thumbnail': metadata['thumbnail'],
                    'channel': metadata['channel']
                })

        context['fav_videos_top_ten'] = vids_top_ten
        return context

    def add_wh_statistics_to_context(self, context, watch_history,
                                     video_ids, n_donations=1, example=False):
        """Add watch history statistics to the context."""
        n_vids_per_day = len(watch_history) / context['dates']['wh_date_range'].days

        # Add overall statistics.
        context.setdefault('watch_stats', {}).update({
            'n_videos_overall': len(watch_history),
            'n_videos_unique_overall': len(set(video_ids)),
            'n_videos_mean_overall': len(watch_history) / n_donations,
            'n_videos_per_day': round(n_vids_per_day, 2)
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
            'n_videos_interval': len(wh_interval),
            'n_videos_unique_interval': len(set(wh_interval_ids)),
            'n_videos_mean_interval': len(wh_interval) / n_donations,
            'n_videos_per_interval': len(wh_interval_ids) / interval_length,
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

    def add_sh_statistics_to_context(
            self,
            context: dict,
            search_history: list[dict],
            n_donations: int = 1,
            example: bool = False
    ) -> dict:
        """
        Add search history statistics for both overall activities and activities
        in a classroom reference interval to the context.

        Args:
            context (dict): The template context.
            search_history (list[dict]): The list of searches.
            n_donations (int): The number of donations the statistics are based on.
            example (bool): Whether it is an example report.

        Returns:
            dict: The updated context.
        """
        if not example:
            interval_min, interval_max = self.classroom.get_reference_interval()
        else:
            interval_min, interval_max = datetime.now() - timedelta(days=30), datetime.now()

        sh_interval = shared_data_utils.get_entries_in_date_range(
            search_history, interval_min, interval_max, 'Date')
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
    def add_sh_plot_to_context(context: dict, search_terms: list[str]):
        """
        Add search history plot to the context (as 'search_plot').

        Args:
            context (dict): The template context.
            search_terms (list[str]): The list of search terms.

        Returns:
            dict: The updated context.
        """
        context['search_plot'] = plot_utils.get_searches_plot(search_terms)
        return context

    @staticmethod
    def add_sh_wordcloud_to_context(
            context: dict,
            search_terms: list[str]
    ) -> dict:
        """
        Add search wordcloud to the context (as 'search_wordcloud').

        Args:
            context (dict): The template context.
            search_terms (list[str]): The list of search terms.

        Returns:
            dict: The updated context.
        """
        context['search_wordcloud'] = shared_plot_utils.create_word_cloud(search_terms)
        return context


class TikTokReportIndividual(BaseReportIndividual, TikTokBaseReport):
    """Base class to generate an individual report for the YouTube data."""
    template_name = 'reports/tiktok/individual_report.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        donated_data = self.get_donations()

        # Add watch history (wh) data to context.
        wh_data = donated_data.get(BLUEPRINT_NAMES['WATCH_HISTORY'])
        if wh_data is not None:
            context.update(self.get_watch_context(wh_data['data']))

        # Add search history (sh) data to context.
        sh_data = donated_data.get(BLUEPRINT_NAMES['SEARCH_HISTORY'])
        if sh_data is not None:
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

    def get_search_context(
            self,
            search_history: list[dict],
            is_example: bool = False
    ) -> dict:
        """
        Add search history related statistics and plots to the context.

        Args:
            search_history (list[dict]): The list of searches.
            is_example (bool): Indicates whether report is using example
                (= synthetic) or actual data.

        Returns:
            dict: A dictionary containing the template variables related to
                the search history.
        """
        context = {}
        if search_history is None:
            context['search_available'] = False
            return context
        context['search_available'] = True

        search_terms = [t['SearchTerm'] for t in search_history]
        normalized_terms = normalize_texts(search_terms)

        self.add_sh_statistics_to_context(context, search_history, example=is_example)

        self.add_sh_plot_to_context(context, search_terms)

        self.add_sh_wordcloud_to_context(context, normalized_terms)

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

        # Search history (sh).
        sh_data = donated_data.get(BLUEPRINT_NAMES['SEARCH_HISTORY'])
        if sh_data is not None:
           context.update(self.get_search_context(sh_data))

        n_donations = [
            len(v) for k, v in donated_data.items()
            if v is not None
        ]
        context['n_participants'] = max(n_donations)
        context['participation_date'] = None
        return context

    def get_watch_context(self, data):
        """Add watch history related statistics and plots to the context."""
        # TODO: optimize the times these statistics are computed.
        context = {}
        if data is None:
            context['wh_available'] = False
            return context
        context['wh_available'] = True

        # Prepare data.
        n_donations = len(data)

        whs_individual = []
        wh_combined = []
        wh_combined_ids_sets = []
        whs_individual_dates = []

        for entry in data:
            wh = entry['data']
            whs_individual.append(wh)
            wh_combined.extend(wh)

            # Extract IDs and dates
            wh_ids = data_utils.get_video_ids(wh)
            wh_dates = data_utils.get_date_list(wh)

            wh_combined_ids_sets.extend(set(wh_ids))
            whs_individual_dates.append(wh_dates)

        wh_combined_ids = data_utils.get_video_ids(wh_combined)
        wh_combined_dates = data_utils.get_date_list(wh_combined)

        # Add information to context.
        self.add_wh_date_infos_to_context(
            context,  wh_combined_dates)

        self.add_wh_statistics_to_context(
            context, wh_combined, wh_combined_ids, n_donations)

        self.add_favorite_videos_to_context(
            context, wh_combined_ids_sets)

        self.add_wh_timeseries_plots_to_context(
            context, whs_individual_dates,
            context['dates']['wh_dates_min'], context['dates']['wh_dates_max']
        )

        self.add_wh_heatmap_plots_to_context(context, wh_combined_dates)
        return context

    def get_search_context(self, search_histories: list[dict]) -> dict:
        """
        Add search history related statistics and plots to the context.

        Args:
            search_histories (list[dict]): A list of search history donations.

        Returns:
            dict: A dictionary containing the template variables related to
                the search histories.
        """
        context = {}
        if search_histories is None:
            context['sh_available'] = False
            return context
        context['sh_available'] = True

        # Prepare data.
        sh_combined = []
        shs_individual = []
        search_terms_individual = []

        for entry in search_histories:
            sh = entry['data']
            sh_combined.extend(sh)
            shs_individual.append(sh)

            # Extract search terms.
            sh_terms = [t['SearchTerm'] for t in sh]
            if sh_terms:
                search_terms_individual.extend(set(sh_terms))

        search_terms_combined = [t['SearchTerm'] for t in sh_combined]

        # Normalize search terms.
        normalized_terms_combined = normalize_texts(search_terms_combined)
        normalized_terms_individual = normalize_texts(search_terms_individual)

        # Identify terms used by at least 2 people.
        term_counter = Counter(normalized_terms_individual)
        allowed_search_terms = {term for term, count in term_counter.items() if count > 1}
        terms_for_plot = [t for t in normalized_terms_combined if t in allowed_search_terms]

        # Add information to context.
        self.add_sh_statistics_to_context(
            context, sh_combined, len(search_histories))

        # Add wordcloud.
        self.add_sh_wordcloud_to_context(context, terms_for_plot)

        return context

class TikTokExampleReport(TikTokReportIndividual, TemplateView):
    template_name = 'reports/tiktok/example_report.html'

    def register_classroom(self):
        """Register classroom object."""
        self.classroom = None

    def register_project(self):
        """Register project object."""
        self.project = None

    def check_classroom_active(self):
        return True

    def get_data(self):
        """ Generate synthetic data for example report. """
        return

    def add_meta_info_to_context(
            self,
            context: dict,
            expiration_date: datetime | None = None
    ) -> dict:
        """
        Adds the following meta information to the context:
        - 'participation_date'
        - 'expiration_date'
        - 'class_id'
        - 'class_name'

        Args:
            context (dict):  The template context.
            expiration_date (datetime.datetime): The date until which the report
                is available.

        Returns:
            dict: The updated context.
        """
        context['participation_date'] = timezone.now().date()
        context['expiration_date'] = 'Dieser Beispielreport ist unbeschränkt verfügbar'
        context['class_id'] = '1234567890'
        context['class_name'] = 'Beispielklasse'
        return context

    def get_context_data(self, **kwargs):
        """
        Load synthetic data for example report, generate plots and statistics
        and add to context.
        """
        context = {}

        # Generate synthetic data.
        start_date = timezone.now().date() - timedelta(days=5)
        wh_data = generate_synthetic_watch_history(start_date)
        sh_data = generate_synthetic_search_history(start_date)

        # Add watch history (wh) data to context.
        context.update(self.get_watch_context(wh_data['data']))

        # Add search history (sh) data to context.
        context.update(self.get_search_context(sh_data['data'], is_example=True))

        # Add metadata to context.
        context = self.add_meta_info_to_context(context)
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
