from collections import Counter
from datetime import datetime, timedelta

import pandas as pd
from django.utils import timezone

from digital_meal.reports.utils.shared import (
    data as shared_data_utils,
    plots as shared_plot_utils
)
from digital_meal.reports.utils.youtube import (
    data as data_utils,
    plots as plot_utils
)
import digital_meal.reports.views.base as base_views
from digital_meal.reports.utils.youtube.data import (
    extract_watch_history_data,
    WatchHistoryData,
    SearchHistoryData,
    extract_search_history_data
)
from digital_meal.reports.utils.youtube.example_data import (
    generate_synthetic_watch_history,
    generate_synthetic_search_history
)
from digital_meal.tool.models import Classroom

import logging
logger = logging.getLogger(__name__)

BLUEPRINT_NAMES = {
    'WATCH_HISTORY': 'Angesehene Videos',
    'SEARCH_HISTORY': 'Suchverlauf',
    'SUBSCRIPTIONS': 'Abonnierte Kanäle'
}

# BASE REPORTS
class YouTubeClassReport(base_views.ClassReport):
    """Base class to generate a class report for the YouTube data."""
    template_name = 'reports/youtube/class_report.html'
    model = Classroom


class YouTubeIndividualReport(base_views.IndividualReport):
    """Base class to generate an individual report for the YouTube data."""
    template_name = 'reports/youtube/individual_report.html'


class YouTubeExampleReport(base_views.ExampleReport):
    """Base class to generate an example report for the YouTube data."""
    template_name = 'reports/youtube/example_report.html'


# WATCH HISTORY REPORT SECTIONS
class WatchHistorySectionsMixin(base_views.BlueprintReportMixin):
    """Adds the data needed to render the report sections based on the watch history.

    Must be used together with either GetDonationClassMixin or
    GetDonationIndividualMixin.
    """

    blueprint_names: list[str] = [BLUEPRINT_NAMES['WATCH_HISTORY']]
    wh_data: WatchHistoryData = None

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
                self.wh_data['videos'],
                self.wh_data['video_ids'],
                self.wh_data['watch_dates'],
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
            context['fav_videos_top_ten'] = self.get_favorite_videos(
                self.wh_data['videos'],
                self.wh_data['video_ids'],
                10
            )
        except (TypeError, ValueError, ZeroDivisionError) as e:
            self.log_error('get_favorite_videos', e)
            pass

        try:
            context['dates_plots'] = self.get_timeseries_plots(
                [self.wh_data['watch_dates']],
                context['stats_overall']['dates_min'],
                context['stats_overall']['dates_max']
            )
        except (TypeError, ValueError, ZeroDivisionError) as e:
            self.log_error('get_timeseries_plots', e)
            pass

        try:
            context.update(
                self.get_heatmap_plots(self.wh_data['watch_dates'])
            )
        except (TypeError, ValueError, ZeroDivisionError) as e:
            self.log_error('get_heatmap_plots', e)
            pass

        try:
            context['channel_plot'] = plot_utils.get_channel_plot(self.wh_data['channels'])
        except (TypeError, ValueError, ZeroDivisionError) as e:
            self.log_error('get_channel_plot', e)
            pass

        try:
            context['n_distinct_channels'] = len(set(self.wh_data['channels']))
        except (TypeError, ValueError, ZeroDivisionError) as e:
            self.log_error('n_distinct_channels', e)
            pass

        return context

    @staticmethod
    def get_overall_statistics(
            watch_history: list[dict],
            video_ids: list[str],
            date_list: list[datetime],
            n_donations: int = 1,
    ) -> dict:
        """Get general watch history statistics for overall use.

        Args:
            watch_history: The list of watched videos.
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
            n_videos_per_day = len(watch_history)
        else:
            n_videos_per_day = len(watch_history) / date_range.days

        statistics = {
            'dates_min': min_date,
            'dates_max': max_date,
            'date_range': max_date - min_date,
            'n_videos': len(watch_history),
            'n_videos_unique': len(set(video_ids)),
            'n_videos_mean': len(watch_history) / n_donations,
            'n_videos_per_day': round(n_videos_per_day, 2)
        }

        return statistics

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
            watch_history, interval_min, interval_max)
        wh_interval_ids = data_utils.get_video_ids(wh_interval)

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
    def get_favorite_videos(
            watch_history: list[dict],
            video_ids: list[str],
            top_n: int = 10,
    ) -> list[dict]:
        """Get the top videos that were watched most often.

        Args:
            watch_history: The list of watched videos.
            video_ids: The list of video ids.
            top_n: Number of videos to return.

        Returns:
            list: Containing information on the n top videos.
        """

        video_titles = data_utils.get_video_title_dict(watch_history)
        most_popular_videos = pd.Series(video_ids).value_counts()[:top_n]

        top_videos = [
            {
                'id': video_id,
                'count': count,
                'title': data_utils.clean_video_title(video_titles.get(video_id))
            }
            for video_id, count in most_popular_videos.items()
        ]

        return top_videos

    @staticmethod
    def get_timeseries_plots(
            date_list: list[list[datetime]],
            min_date: datetime,
            max_date: datetime
    ) -> dict:
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

        # Plot with daily bins.
        dates_days = shared_data_utils.get_summary_counts_per_date(
            date_list, 'd', 'mean')
        dates_plot_days = shared_plot_utils.get_timeseries_plot(
            pd.Series(dates_days),
            date_min=min_date,
            date_max=max_date
        )

        # Plot with weekly bins.
        dates_weeks = shared_data_utils.get_summary_counts_per_date(
            date_list, 'w', 'mean')
        dates_plot_weeks = shared_plot_utils.get_timeseries_plot(
            pd.Series(dates_weeks), bin_width=7,
            date_min=min_date, date_max=max_date)

        # Plot with monthly bins.
        dates_months = shared_data_utils.get_summary_counts_per_date(
            date_list, 'm', 'mean')
        dates_plot_months = shared_plot_utils.get_timeseries_plot(
            pd.Series(dates_months), bin_width=30,
            date_min=min_date, date_max=max_date)

        # Plot with yearly bins.
        dates_years = shared_data_utils.get_summary_counts_per_date(
            date_list, 'y', 'mean')
        dates_plot_years = shared_plot_utils.get_timeseries_plot(
            pd.Series(dates_years), bin_width=365,
            date_min=min_date, date_max=max_date)

        dates_plots = {
            'days': dates_plot_days,
            'weeks': dates_plot_weeks,
            'months': dates_plot_months,
            'years': dates_plot_years
        }

        return dates_plots

    @staticmethod
    def get_heatmap_plots(date_list: list[datetime]) -> dict:
        """Generate watch history heatmap plots for mean hours and per weekday.

        Args:
            date_list: The list of datetimes of watched videos.

        Returns:
            dict: With a key for each plot type 'weekday_use_plot', 'hours_plot',
                each holding a {'div': _, 'script': _} value.
        """

        return {
            'weekday_use_plot': shared_plot_utils.get_weekday_use_plot(date_list),
            'hours_plot': shared_plot_utils.get_day_usetime_plot(date_list)
        }


class WatchHistorySectionsClassMixin(WatchHistorySectionsMixin):

    def clean_blueprint_donation_data(self, donation_data: list) -> WatchHistoryData:
        return extract_watch_history_data(donation_data, keep_separate=True)

    def get_context_data(self, **kwargs) -> dict:
        context = super().get_context_data(**kwargs)

        # Extend class report with most watched channels plot.
        try:
            context['most_watched_channels'] = self.get_most_watched_channels(
                self.wh_data['channels_separate'],
            )
        except (TypeError, ValueError, ZeroDivisionError) as e:
            self.log_error('get_most_watched_channels', e)
            pass

        context['n_participants'] = self.wh_data['n_participants']
        return context

    @staticmethod
    def get_most_watched_channels(
            channel_lists: list[list[str]]
    ) -> dict:
        """Get information on the most watched channels.

        Information is used to render the
        'most_watched_channels_section_class.html' report section.

        Args:
            channel_lists: List of lists containing the watched channels data
                for each person.

        Returns:
            dict: Most watched channels information, including 'n_unique',
                'n_multiple', 'share_multiple', and 'channel_list_top_10'.
        """
        # Prepare data.
        combined_channel_history = []
        channel_sets = []
        for channel_list in channel_lists:
            combined_channel_history.extend(channel_list)
            channel_sets.extend(set(channel_list))

        # Get the names of channels viewed by more than one person.
        channel_counts = pd.Series(channel_sets).value_counts()
        multi_viewer_channel_names = set(
            channel_counts[channel_counts > 1].index.tolist()
        )

        # Get a list of all videos watched by channels viewed by more than one person.
        considered_channels = [
            channel for channel in combined_channel_history
            if channel in multi_viewer_channel_names
        ]

        # Identify most watched channels.
        considered_channel_counts = pd.Series(considered_channels).value_counts()
        top_ten_channels = considered_channel_counts[:10]

        # Compute context variables
        n_unique = len(set(combined_channel_history))
        n_multiple = len(multi_viewer_channel_names)

        if n_unique and n_unique > 0:
            share_multiple = round((n_multiple / n_unique), 2)
        else:
            share_multiple = 0

        return {
            'n_unique': n_unique,
            'n_multiple': n_multiple,
            'share_multiple': share_multiple,
            'channel_list_top_10': top_ten_channels
        }


class WatchHistorySectionsClass(
    WatchHistorySectionsClassMixin,
    base_views.GetDonationsClassMixin,
    base_views.ClassReport
):
    """Renders sections for individual report."""
    template_name = 'reports/youtube/_watch_history_report_class.html'


class WatchHistorySectionsIndividual(
    WatchHistorySectionsMixin,
    base_views.GetDonationsIndividualMixin,
    base_views.IndividualReport
):
    """Renders sections for individual report."""
    template_name = 'reports/youtube/_watch_history_report_individual.html'


class WatchHistorySectionsExample(
    WatchHistorySectionsMixin,
    base_views.GetDonationsMixin,
    base_views.ExampleReport
):
    """Renders sections for example report."""
    template_name = 'reports/youtube/_watch_history_report_individual.html'

    def add_donations(self) -> None:
        """Overwrites original function, because example data is not retrieved from db."""
        return None

    def load_blueprint_donation_data(self, *args, **kwargs) -> list[list]:
        """Overwrites original function to return synthetic donation data.

        Returns:
            list: A dictionary mimicking the YouTube watch history JSON format.
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

    def get_terms_for_wordcloud(self) -> list[str]:
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

    @staticmethod
    def get_search_history_statistics(
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
            reference_interval[1]
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


class SearchHistorySectionsClass(
    SearchHistorySectionsMixin,
    base_views.GetDonationsClassMixin,
    base_views.ClassReport
):
    """Renders sections for individual report."""
    template_name = 'reports/youtube/_search_history_report_class.html'


class SearchHistorySectionsIndividual(
    SearchHistorySectionsMixin,
    base_views.GetDonationsIndividualMixin,
    base_views.IndividualReport
):
    """Renders sections for individual report."""
    template_name = 'reports/youtube/_search_history_report_individual.html'


class SearchHistorySectionsExample(
    SearchHistorySectionsMixin,
    base_views.GetDonationsMixin,
    base_views.ExampleReport
):
    """Renders sections for example report."""
    template_name = 'reports/youtube/_search_history_report_individual.html'

    def add_donations(self) -> None:
        """Overwrites original function, because example data is not retrieved from db."""
        return None

    def load_blueprint_donation_data(self, *args, **kwargs) -> list[list]:
        """Overwrites original function to return synthetic donation data.

        Returns:
            list: A dictionary mimicking the YouTube watch history JSON format.
        """
        start_date = timezone.now().date() - timedelta(days=5)
        synthetic_data = generate_synthetic_search_history(start_date)
        return [synthetic_data['data']]


# SUBSCRIPTION REPORT SECTIONS
class SubscriptionSectionMixin(base_views.BlueprintReportMixin):
    """Adds the data needed to render the subscriptions report sections.

    Must be used together with either GetDonationClassMixin or
    GetDonationIndividualMixin.
    """

    blueprint_names: list[str] = [BLUEPRINT_NAMES['SUBSCRIPTIONS']]
    sub_data: list

    def clean_blueprint_donation_data(
            self,
            donation_data: list[list]
    ) -> list:
        return donation_data

    def get_context_data(self, **kwargs) -> dict:
        context = super().get_context_data(**kwargs)

        # Get the data needed to generate plots and stats.
        self.sub_data = self.get_blueprint_donation_data(BLUEPRINT_NAMES['SUBSCRIPTIONS'])
        if self.sub_data is None or not self.sub_data:
            logger.info('Subscription sections: data did not contain any valid search terms.')
            context['subs_available'] = False
            return context

        context['subs_available'] = True

        # Generate plots and stats
        try:
            context.update(self.get_sub_data())
        except (TypeError, ValueError, ZeroDivisionError) as e:
            self.log_error('get_sub_data', e)
            pass

        return context

    def get_sub_data(self):
        """Get subscription information.

        Get statistics and plot for loaded subscription information.

        Returns:
            dict: Subscription information, including 'plot', 'n_distinct', and
                'n_more_than_one'.
        """
        # Combine the subscription data of all individuals in one list.
        combined_subs = []
        for subscription_list in self.sub_data:
            combined_subs.extend(subscription_list)

        combined_subs = data_utils.clean_channel_list(combined_subs)
        channel_titles = [entry['title'] for entry in combined_subs]

        # Get number of unique subscribed channels in class.
        n_subs_distinct = len(set(channel_titles))

        # Get list of channels with min. 2 subscribers in the class.
        counter = Counter(channel_titles)
        subs_more_than_one_person = [
            item for item in channel_titles if counter[item] > 1]
        n_subs_more_than_one = len(subs_more_than_one_person)

        # Create graph.
        subs_plot = plot_utils.get_subscription_plot(subs_more_than_one_person)

        # Return subscription data.
        return {
            'plot': subs_plot,
            'n_distinct': n_subs_distinct,
            'n_more_than_one': n_subs_more_than_one
        }


class SubscriptionSectionsClass(
    SubscriptionSectionMixin,
    base_views.GetDonationsClassMixin,
    base_views.ClassReport
):
    """Renders sections for individual report."""
    template_name = 'reports/youtube/_subscriptions_report_class.html'
