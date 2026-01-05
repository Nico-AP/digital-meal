import time
from collections import Counter
from datetime import datetime, timedelta

import pandas as pd
import requests
from django.utils import timezone

import digital_meal.reports.views.base as base_views
from digital_meal.reports.utils.shared import (
    data as shared_data_utils,
    plots as shared_plot_utils,
)
from digital_meal.reports.utils.tiktok.data import (
    extract_watch_history_data,
    WatchHistoryData,
    SearchHistoryData,
    extract_search_history_data,
    get_video_metadata
)
from digital_meal.reports.utils.tiktok.example_data import (
    generate_synthetic_watch_history,
    generate_synthetic_search_history
)
from digital_meal.tool.models import Classroom

import logging_utils
logger = logging.getLogger(__name__)

BLUEPRINT_NAMES = {
    'WATCH_HISTORY': 'Angesehene Videos',
    'SEARCH_HISTORY': 'Durchgeführte Suchen'
}

# BASE REPORTS
class TikTokClassReport(base_views.ClassReport):
    """Base class to generate a class report for the TikTok data."""
    template_name = 'reports/tiktok/class_report.html'
    model = Classroom


class TikTokIndividualReport(base_views.IndividualReport):
    """Base class to generate an individual report for the TikTok data."""
    template_name = 'reports/tiktok/individual_report.html'


class TikTokExampleReport(base_views.ExampleReport):
    """Base class to generate an example report for the TikTok data."""
    template_name = 'reports/tiktok/example_report.html'


# WATCH HISTORY REPORT SECTIONS
class WatchHistorySectionsMixin(base_views.BlueprintReportMixin):
    """Adds the data needed to render the report sections based on the watch history.

    Must be used together with either GetDonationClassMixin or
    GetDonationIndividualMixin.
    """

    blueprint_names: list[str] = [BLUEPRINT_NAMES['WATCH_HISTORY']]
    wh_data: WatchHistoryData

    def clean_blueprint_donation_data(
            self,
            donation_data: list[list]
    ) -> WatchHistoryData:
        return extract_watch_history_data(donation_data)

    def get_context_data(self, **kwargs) -> dict:
        context = super().get_context_data(**kwargs)

        # Get the data needed to generate plots and stats.
        self.wh_data = self.get_blueprint_donation_data(BLUEPRINT_NAMES['WATCH_HISTORY'])
        if self.wh_data is None or not self.wh_data.get('video_ids'):
            logger.info('Watch history sections: data did not contain any valid videos.')
            context['wh_available'] = False
            return context

        context['wh_available'] = True
        context['n_participants'] = self.wh_data.get('n_participants')

        # Generate plots and stats
        try:
            context['stats_overall'] = self.get_overall_statistics(
                self.wh_data['video_ids'],
                self.wh_data['video_dates'],
                self.wh_data['n_participants']
            )
        except (TypeError, ValueError, ZeroDivisionError) as e:
            self.log_error('get_overall_statistics', e)
            pass

        try:
            if self.report_type == base_views.REPORT_TYPES['EXAMPLE']:
                interval_min = datetime.now() - timedelta(days=30)
                interval_max = datetime.now()
            else:
                interval_min, interval_max = self.classroom.get_reference_interval()

            context['stats_interval'] = self.get_interval_statistics(
                self.wh_data['videos'],
                (interval_min, interval_max),
                self.wh_data['n_participants']
            )
        except (TypeError, ValueError, ZeroDivisionError) as e:
            self.log_error('get_interval_statistics', e)
            pass

        try:
            context['dates_plots'] = self.get_timeseries_plots(
                [self.wh_data['video_dates']],
                context['stats_overall']['dates_min'],
                context['stats_overall']['dates_max']
            )
        except (TypeError, ValueError, ZeroDivisionError) as e:
            self.log_error('get_timeseries_plots', e)
            pass

        try:
            context['fav_videos_top_ten'] = self.get_favorite_videos(
                self.wh_data['video_ids'], 10)
        except (TypeError, ValueError, ZeroDivisionError) as e:
            self.log_error('get_favorite_videos', e)
            pass

        try:
            context.update(self.get_heatmap_plots(self.wh_data['video_dates']))
        except (TypeError, ValueError, ZeroDivisionError) as e:
            self.log_error('get_heatmap_plots', e)
            pass

        return context

    @staticmethod
    def get_overall_statistics(
            video_ids: list[str],
            date_list: list[datetime],
            n_donations: int = 1,
    ) -> dict:
        """Get general watch history statistics for overall use.

        Args:
            video_ids: The list of video ids.
            date_list: The list of dates of watched videos.
            n_donations: The number of donations the statistics are based on.

        Returns:
            dict: Containing the watch history statistics.
        """

        min_date = min(date_list)
        max_date = max(date_list)
        date_range = max_date - min_date

        if date_range == 0:
            n_videos_per_day = len(video_ids)
        else:
            n_videos_per_day = len(video_ids) / date_range.days

        return {
            'dates_min': min_date,
            'dates_max': max_date,
            'date_range': date_range,
            'n_videos': len(video_ids),
            'n_videos_unique': len(set(video_ids)),
            'n_videos_mean': len(video_ids) / n_donations,
            'n_videos_per_day': round(n_videos_per_day, 2)
        }

    @staticmethod
    def get_interval_statistics(
            watch_history: list[dict],
            reference_interval: tuple[datetime, datetime],
            n_donations: int = 1
    ) -> dict:
        """Get general watch history statistics for classroom reference interval.

        Args:
            watch_history: The list of watched videos.
            reference_interval: The reference interval as a tuple (start, end).
            n_donations: The number of donations the statistics are based on.

        Returns:
            dict: Containing the watch history statistics.
        """
        interval_min = reference_interval[0]
        interval_max = reference_interval[1]
        interval_length = (interval_max - interval_min).days

        wh_interval = shared_data_utils.get_entries_in_date_range(
            watch_history,
            interval_min,
            interval_max,
            'Date'
        )
        wh_interval_ids = [e['id'] for e in wh_interval]

        interval_statistics = {
            'date_min': interval_min,
            'date_max': interval_max,
            'n_videos': len(wh_interval),
            'n_videos_unique': len(set(wh_interval_ids)),
            'n_videos_mean': len(wh_interval) / n_donations,
            'n_videos_per_interval': len(wh_interval_ids) / interval_length,
        }

        return interval_statistics

    @staticmethod
    def get_timeseries_plots(
            date_list: list[list[datetime]],
            min_date: datetime,
            max_date: datetime
    ):
        """Generate timeseries plots.

        Generates plots based on daily, weekly, monthly, and yearly data.

        Args:
            date_list: The list of datetimes of watched videos.
            min_date: The first date to be included in the plots.
            max_date: The last date to be included in the plots.

        Returns:
            dict: With a key for each plot type 'days', 'weeks', 'months', 'years',
                each holding a {'div': _, 'script': _} value.
        """
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

        return {
            'days': dates_plot_days,
            'weeks': dates_plot_weeks,
            'months': dates_plot_months,
            'years': dates_plot_years
        }

    @staticmethod
    def get_favorite_videos(video_ids: list[str], top_n: int = 10) -> list[dict]:
        """Get the top n videos that were watched most often."""
        most_popular_videos = pd.Series(video_ids).value_counts()[:top_n]

        with requests.Session() as session:
            top_videos = []
            for key, value in most_popular_videos.items():
                metadata = get_video_metadata(key, session)
                time.sleep(0.1)
                top_videos.append({
                    'id': key,
                    'count': value,
                    'thumbnail': metadata['thumbnail'],
                    'channel': metadata['channel']
                })

        return top_videos

    @staticmethod
    def get_heatmap_plots(date_list: list[datetime]) -> dict:
        """Add watch history heatmap plots to the context."""
        return {
            'weekday_use_plot': shared_plot_utils.get_weekday_use_plot(date_list),
            'hours_plot': shared_plot_utils.get_day_usetime_plot(date_list)
        }


class WatchHistorySectionsClassMixin(WatchHistorySectionsMixin):

    def clean_blueprint_donation_data(self, donation_data: list) -> WatchHistoryData:
        return extract_watch_history_data(donation_data, keep_separate=True)


class WatchHistorySectionsClass(
    WatchHistorySectionsClassMixin,
    base_views.GetDonationsClassMixin,
    base_views.ClassReport
):
    """Renders sections for individual report."""
    template_name = 'reports/tiktok/_watch_history_report_class.html'


class WatchHistorySectionsIndividual(
    WatchHistorySectionsMixin,
    base_views.GetDonationsIndividualMixin,
    base_views.IndividualReport
):
    """Renders sections for individual report."""
    template_name = 'reports/tiktok/_watch_history_report_individual.html'


class WatchHistorySectionsExample(
    WatchHistorySectionsMixin,
    base_views.GetDonationsMixin,
    base_views.ExampleReport
):
    """Renders sections for example report."""
    template_name = 'reports/tiktok/_watch_history_report_individual.html'

    def add_donations(self) -> None:
        """Overwrites original function, because example data is not retrieved from db."""
        return None

    def load_blueprint_donation_data(self, *args, **kwargs) -> list[list]:
        """Overwrites original function to return synthetic donation data.

        Returns:
            list: A dictionary mimicking the TikTok watch history JSON format.
        """
        start_date = timezone.now().date() - timedelta(days=5)
        synthetic_data = generate_synthetic_watch_history(start_date)
        return [synthetic_data['data']]


# SEARCH HISTORY REPORT SECTIONS
class SearchHistorySectionsMixin(base_views.BlueprintReportMixin):
    """Adds the data needed to render the search history report sections.

    Must be used together with either GetDonationClassMixin or
    GetDonationIndividualMixin.
    """

    blueprint_names: list[str] = [BLUEPRINT_NAMES['SEARCH_HISTORY']]
    sh_data: SearchHistoryData = None

    def clean_blueprint_donation_data(
            self,
            donation_data: list[list]
    ) -> SearchHistoryData:
        if self.report_type == base_views.REPORT_TYPES['CLASS']:
            return extract_search_history_data(donation_data, keep_separate=True)
        else:
            return extract_search_history_data(donation_data)

    def get_context_data(self, **kwargs) -> dict:
        context = super().get_context_data(**kwargs)

        # Get the data needed to generate plots and stats.
        self.sh_data = self.get_blueprint_donation_data(BLUEPRINT_NAMES['SEARCH_HISTORY'])
        if self.sh_data is None or not self.sh_data.get('search_terms'):
            logger.info('Search history sections: data did not contain any valid search terms.')
            context['sh_available'] = False
            return context

        context['sh_available'] = True

        # Generate plots and stats
        try:
            if self.report_type == base_views.REPORT_TYPES['EXAMPLE']:
                interval_min = datetime.now() - timedelta(days=30)
                interval_max = datetime.now()
            else:
                interval_min, interval_max = self.classroom.get_reference_interval()

            context.update(
                self.get_search_history_statistics(
                    self.sh_data['searches'],
                    (interval_min, interval_max),
                    self.sh_data['n_participants']
                )
            )
        except (TypeError, ValueError, ZeroDivisionError) as e:
            self.log_error('get_search_history_statistics', e)
            pass

        try:
            terms_for_plot = self.get_terms_for_wordcloud()
            context['search_wordcloud'] = shared_plot_utils.create_word_cloud(terms_for_plot)
        except (TypeError, ValueError, ZeroDivisionError) as e:
            self.log_error('shared_plot_utils.create_word_cloud', e)
            pass

        return context

    @staticmethod
    def get_search_history_statistics(    # TODO: Check if this can be moved to shared view
            search_history: list[dict],
            reference_interval: tuple[datetime, datetime],
            n_donations: int,
    ) -> dict:
        """Get search history statistics.

        Get statistics for both overall activities and activities in a
        reference interval.

        Args:
            search_history: The list of searches.
            reference_interval: The reference interval as a tuple (start, end).
            n_donations: The number of donations the statistics are based on.

        Returns:
            dict: search history statistics.
        """

        sh_interval = shared_data_utils.get_entries_in_date_range(
            search_history,
            reference_interval[0],
            reference_interval[1],
            'Date'
        )

        return {
            # Statistics overall.
            'n_searches': len(search_history),
            'n_searches_mean': len(search_history) / n_donations,
            # Statistics interval
            'date_min': reference_interval[0],
            'date_max': reference_interval[1],
            'n_searches_interval': len(sh_interval),
            'n_searches_mean_interval': len(sh_interval) / n_donations
        }

    def get_terms_for_wordcloud(self) -> list[str]:  # TODO: Check if this can be moved to shared view
        """Get normalized search terms.

        For class reports, only search terms that appear in there normalized
        form in the watch histories of at least two participants will be
        included.
        """
        if self.report_type != base_views.REPORT_TYPES['CLASS']:
            return shared_data_utils.normalize_texts(self.sh_data['search_terms'])

        # Class report:
        # Normalize search terms.
        normalized_per_history = []
        normalized_combined = []
        for search_terms in self.sh_data['search_terms_separate']:
            unique_search_terms = list(set(search_terms))
            normalized = shared_data_utils.normalize_texts(unique_search_terms)
            normalized_per_history.append(normalized)
            normalized_combined.extend(normalized)

        # Identify terms used by at least 2 people.
        unique_per_history = []
        for normalized_terms in normalized_per_history:
            unique_per_history.extend(normalized_terms)
        term_counter = Counter(unique_per_history)
        allowed_search_terms = {term for term, count in term_counter.items() if count > 1}

        terms_for_plot = [t for t in normalized_combined if t in allowed_search_terms]
        return terms_for_plot


class SearchHistorySectionsClass(
    SearchHistorySectionsMixin,
    base_views.GetDonationsClassMixin,
    base_views.ClassReport
):
    """Renders sections for individual report."""
    template_name = 'reports/tiktok/_search_history_report_class.html'


class SearchHistorySectionsIndividual(
    SearchHistorySectionsMixin,
    base_views.GetDonationsIndividualMixin,
    base_views.IndividualReport
):
    """Renders sections for individual report."""
    template_name = 'reports/tiktok/_search_history_report_individual.html'


class SearchHistorySectionsExample(
    SearchHistorySectionsMixin,
    base_views.GetDonationsMixin,
    base_views.ExampleReport
):
    """Renders sections for example report."""
    template_name = 'reports/tiktok/_search_history_report_individual.html'

    def add_donations(self) -> None:
        """Overwrites original function, because example data is not retrieved from db."""
        return None

    def load_blueprint_donation_data(self, *args, **kwargs) -> list[list]:
        """Overwrites original function to return synthetic donation data.

        Returns:
            list: A dictionary mimicking the TikTok watch history JSON format.
        """
        start_date = timezone.now().date() - timedelta(days=5)
        synthetic_data = generate_synthetic_search_history(start_date)
        return [synthetic_data['data']]
