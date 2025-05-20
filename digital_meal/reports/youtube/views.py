from collections import Counter
from datetime import datetime, timedelta

import pandas as pd
from django.utils import timezone
from django.views.generic import TemplateView

from digital_meal.reports.utils_shared.data_utils import normalize_texts
from digital_meal.reports.youtube import data_utils
from digital_meal.reports.youtube import plot_utils
from digital_meal.reports.youtube.example_data import (
    generate_synthetic_watch_history, generate_synthetic_search_history)
from digital_meal.reports.utils_shared import plot_utils as shared_plot_utils
from digital_meal.reports.utils_shared import data_utils as shared_data_utils
from digital_meal.reports.views import BaseReportClassroom, BaseReportIndividual
from digital_meal.tool.models import Classroom


BLUEPRINT_NAMES = {
    'WATCH_HISTORY': 'Angesehene Videos',
    'SEARCH_HISTORY': 'Suchverlauf',
    'SUBSCRIPTIONS': 'Abonnierte Kanäle'
}


class YouTubeBaseReport:
    """
    Implements shared methods for the generation of YouTube reports.
    """

    @staticmethod
    def add_wh_timeseries_plots_to_context(
            context: dict,
            date_list: list[list[datetime]],
            min_date: datetime,
            max_date: datetime
    ) -> dict:
        """
        Add watch history timeseries plots to the context. Adds the following
        to the context:

        - 'dates_plot_days'
        - 'dates_plot_weeks'
        - 'dates_plot_months'
        - 'dates_plot_years'

        Args:
            context (dict): The template context.
            date_list (list[datetime]): The list of datetimes of watched videos.
            min_date (datetime): The first date to be included in the plots.
            max_date (datetime): The last date to be included in the plots.

        Returns:
            dict: Updated context.
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

        context.update({
            'dates_plot_days': dates_plot_days,
            'dates_plot_weeks': dates_plot_weeks,
            'dates_plot_months': dates_plot_months,
            'dates_plot_years': dates_plot_years
        })
        return context

    @staticmethod
    def add_wh_date_infos_to_context(
            context: dict,
            date_list: list[datetime]
    ) -> dict:
        """
        Adds the following date information related to the watch history
        to the context:

        - dates['wh_dates_min']: Earliest watch date
        - dates['wh_dates_max']: Latest watch date
        - dates['wh_date_range']: Date range of these two dates

        Args:
            context (dict): The template context.
            date_list (list[datetime.datetime]): The list of dates of watched videos.

        Returns:
            dict: The updated context
        """
        context.update({
            'dates': {
                'wh_dates_min': min(date_list),
                'wh_dates_max': max(date_list),
                'wh_date_range': max(date_list) - min(date_list)
            }
        })
        return context

    @staticmethod
    def add_favorite_videos_to_context(
            context: dict,
            watch_history: list[dict],
            video_ids: list[str]
    ) -> dict:
        """
        Add the 10 videos to the context that were watched most often. Adds
        'fav_videos_top_ten' to the context.

        Args:
            context (dict): The template context.
            watch_history (list[dict]): The list of watched videos.
            video_ids (list[str]): The list of video ids.

        Returns:
            dict: The updated context
        """
        video_titles = data_utils.get_video_title_dict(watch_history)
        most_popular_videos = pd.Series(video_ids).value_counts()[:10].to_dict()
        videos_top_ten = []
        for key, value in most_popular_videos.items():
            videos_top_ten.append({
                'id': key,
                'count': value,
                'title': data_utils.clean_video_title(video_titles.get(key))
            })
        context['fav_videos_top_ten'] = videos_top_ten
        return context

    def add_wh_statistics_to_context(
            self,
            context: dict,
            watch_history: list[dict],
            video_ids: list[str],
            n_donations: int = 1,
            example: bool = False
    ) -> dict:
        """
        Add watch history statistics for both overall use and use in a classroom
        reference interval to the context.

        Args:
            context (dict): The template context.
            watch_history (list[dict]): The list of watched videos.
            video_ids (list[str]): The list of video ids.
            n_donations (int): The number of donations the statistics are based on.
            example (bool): Whether it is an example report.

        Returns:
            dict: The updated context.
        """
        n_videos_per_day = len(watch_history) / context['dates']['wh_date_range'].days

        # Add overall statistics.
        context.setdefault('watch_stats', {}).update({
            'n_videos_overall': len(watch_history),
            'n_videos_unique_overall': len(set(video_ids)),
            'n_videos_mean_overall': len(watch_history) / n_donations,
            'n_videos_per_day': round(n_videos_per_day, 2)
        })

        # Add interval statistics
        if not example:
            interval_min, interval_max = self.classroom.get_reference_interval()
        else:
            interval_min, interval_max = datetime.now() - timedelta(days=30), datetime.now()

        if interval_min is None and interval_max is None:
            return context

        interval_length = (interval_max - interval_min).days
        wh_interval = shared_data_utils.get_entries_in_date_range(
            watch_history, interval_min, interval_max)
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
    def add_wh_heatmap_plots_to_context(
            context: dict,
            date_list: list[datetime]
    ) -> dict:
        """
        Add watch history heatmap plots to the context at 'weekday:use_plot'
        and 'hours_plot'.

        Args:
            context (dict): The template context.
            date_list (list[datetime.datetime]): The list of datetimes of watched videos.

        Returns:
            dict: The updated context.
        """
        context.update({
            'weekday_use_plot': shared_plot_utils.get_weekday_use_plot(date_list),
            'hours_plot': shared_plot_utils.get_day_usetime_plot(date_list)
        })
        return context

    @staticmethod
    def add_wh_channel_info_to_context(
            context: dict,
            channels: list[str]
    ) -> dict:
        """
        Add information related to channel occurrence in watch history
        to the context. Includes the number of distinct channels in the
        watch history ('n_distinct_channels') and a barplot showing the
        most occurring channels ('channel_plot').

        Args:
            context (dict): The template context.
            channels (list[str]): The list of channels.
        """
        context.update({
            'channel_plot': plot_utils.get_channel_plot(channels),
            'n_distinct_channels': len(set(channels))
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


class YouTubeReportIndividual(BaseReportIndividual, YouTubeBaseReport):
    """Base class to generate an individual report for the YouTube data."""
    template_name = 'reports/youtube/individual_report.html'

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

    def get_watch_context(
            self,
            watch_history: list[dict],
            is_example: bool = False
    ) -> dict:
        """
        Add statistics and plots related to a persons watch history to
        the context.

        Args:
            watch_history (list[dict]): The list of watched videos.
            is_example (bool): Indicates whether report is using example
                (= synthetic) or actual data.

        Returns:
            dict: A dictionary containing the template variables related to
                the watch history.
        """
        context = {}
        if watch_history is None:
            context['wh_available'] = False
            return context
        context['wh_available'] = True

        # Create list of watched videos and separate lists for ids and dates
        # of watched videos.
        wh_without_ads = data_utils.exclude_google_ads_videos(watch_history)
        wh_ids = data_utils.get_video_ids(wh_without_ads)
        wh_dates = data_utils.get_date_list(wh_without_ads)

        self.add_wh_date_infos_to_context(context, wh_dates)

        self.add_wh_statistics_to_context(
            context, wh_without_ads, wh_ids, example=is_example)

        self.add_favorite_videos_to_context(context, wh_without_ads, wh_ids)

        self.add_wh_timeseries_plots_to_context(
            context,
            [wh_dates],
            context['dates']['wh_dates_min'],
            context['dates']['wh_dates_max']
        )

        self.add_wh_heatmap_plots_to_context(context, wh_dates)

        # Add channel-related information to the context.
        channels = data_utils.get_channel_names_from_history(wh_without_ads)
        self.add_wh_channel_info_to_context(context, channels)
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

        sh_without_ads = data_utils.exclude_ads_from_search_history(search_history)
        sh_without_ads = data_utils.clean_search_titles(sh_without_ads)
        search_terms = data_utils.get_title_list(sh_without_ads)
        normalized_terms = normalize_texts(search_terms)

        self.add_sh_statistics_to_context(context, sh_without_ads, example=is_example)

        self.add_sh_plot_to_context(context, search_terms)

        self.add_sh_wordcloud_to_context(context, normalized_terms)

        return context


class YouTubeReportClassroom(BaseReportClassroom, YouTubeBaseReport):
    """Generates the classroom report for the YouTube data."""
    model = Classroom
    template_name = 'reports/youtube/class_report.html'

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
        wh_data = donated_data.get(BLUEPRINT_NAMES['WATCH_HISTORY'])
        if wh_data is not None:
            context.update(self.get_watch_context(wh_data))

        # Search history (sh).
        sh_data = donated_data.get(BLUEPRINT_NAMES['SEARCH_HISTORY'])
        if sh_data is not None:
            context.update(self.get_search_context(sh_data))

        # Subscribed channels (sc).
        sc_data = donated_data.get(BLUEPRINT_NAMES['SUBSCRIPTIONS'])
        if sc_data is not None:
            context.update(self.get_subscription_context(sc_data))

        # Get maximum number of participants that have donated to the same blueprint.
        n_donations = [
            len(v) for k, v in donated_data.items()
            if v is not None
        ]
        context['n_participants'] = max(n_donations)
        return context

    def get_watch_context(self, watch_histories: list[dict]) -> dict:
        """
        Add watch history related statistics and plots to the context.

        Args:
            watch_histories (list[dict]): A list of watch history donations.

        Returns:
            dict: A dictionary containing the template variables related to
                the watch histories.
        """
        # TODO: optimize the times these statistics are computed.
        context = {}
        if watch_histories is None:
            context['wh_available'] = False
            return context
        context['wh_available'] = True

        # Combine the watch histories of all individuals into one list.
        wh_combined = []
        whs_individual = [
            data_utils.exclude_google_ads_videos(wh['data'])
            for wh in watch_histories
        ]
        for wh in whs_individual:
            wh_combined += wh

        # Get separate lists for the video ids and the dates.
        wh_combined_ids = data_utils.get_video_ids(wh_combined)
        wh_combined_dates = data_utils.get_date_list(wh_combined)

        self.add_wh_date_infos_to_context(context, wh_combined_dates)

        self.add_wh_statistics_to_context(
            context, wh_combined, wh_combined_ids, len(watch_histories))

        # Create a list of the sets of video ids for each individual.
        # Used to determine which videos have been watched at least once
        # by the most individuals.
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
            context,
            whs_individual_dates,
            context['dates']['wh_dates_min'],
            context['dates']['wh_dates_max']
        )

        self.add_wh_heatmap_plots_to_context(context, wh_combined_dates)

        self.add_most_watched_channels_context(context, whs_individual)
        return context

    @staticmethod
    def add_most_watched_channels_context(
            context: dict,
            watch_histories: list[list]
    ) -> dict:
        """
        Takes the view context and adds variables needed to render the
        'most_watched_channels_section_class.html' report section.

        Adds the following variables to the context:
        - most_watched_channels['n_unique']
        - most_watched_channels['n_multiple']
        - most_watched_channels['share_multiple']
        - most_watched_channels['channel_list_top_10']

        Args:
            context (dict): Template context.
            watch_histories (list[list]): List of lists containing the
                watch history data for each person as a list.

        Returns:
            dict: The updated context.
        """
        combined_channel_history = []
        channel_sets = []
        for watch_history in watch_histories:
            channel_history = data_utils.get_channel_names_from_history(watch_history)
            combined_channel_history += channel_history
            channel_sets += list(set(channel_history))

        # Get the names of channels viewed by more than one person.
        channel_counts = pd.Series(channel_sets).value_counts()
        multi_viewer_channel_names = channel_counts[channel_counts > 1].index.tolist()

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

        context.setdefault('most_watched_channels', {}).update({
            'n_unique': n_unique,
            'n_multiple': n_multiple,
            'share_multiple': share_multiple,
            'channel_list_top_10': top_ten_channels
        })
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

        # Remove Google Ads from search histories and combine the histories of
        # all individuals in one list.
        sh_combined = []
        shs_individual = []
        for sh in search_histories:
            sh = data_utils.exclude_ads_from_search_history(sh['data'])
            cleaned_entry = data_utils.clean_search_titles(sh)
            sh_combined += cleaned_entry
            shs_individual.append(cleaned_entry)

        self.add_sh_statistics_to_context(
            context, sh_combined, len(search_histories))

        # Extract search terms from search histories.
        search_terms_combined = data_utils.get_title_list(sh_combined)
        search_terms_individual = []
        for sh in shs_individual:
            sh_terms = data_utils.get_title_list(sh)
            if sh_terms:
                search_terms_individual += list(set(sh_terms))

        # Normalize search terms.
        normalized_terms_combined = normalize_texts(search_terms_combined)
        normalized_terms_individual = normalize_texts(search_terms_individual)

        # Identify terms used by at least 2 people.
        term_counter = Counter(normalized_terms_individual)
        allowed_search_terms = {term for term, count in term_counter.items() if count > 1}
        terms_for_plot = [t for t in normalized_terms_combined if t in allowed_search_terms]

        # Add wordcloud.
        self.add_sh_wordcloud_to_context(context, terms_for_plot)

        return context

    def get_subscription_context(self, channel_subscriptions: list[dict]) -> dict:
        """
        Add subscription related statistics and plots to the context.

        Args:
            channel_subscriptions (list[dict]): A list of channel
                subscription lists donations.

        Returns:
            dict: A dictionary containing the template variables related to
                the subscription lists.
        """
        context = {}
        if channel_subscriptions is None:
            context['sc_available'] = False
            return context
        context['sc_available'] = True

        # Combine the subscription data of all individuals in one list.
        combined_subs = []
        for subscription_list in channel_subscriptions:
            combined_subs += subscription_list['data']
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

        # Add basic subscription statistics to the context.
        context.setdefault('subscriptions', {}).update({
            'plot': subs_plot,
            'n_distinct': n_subs_distinct,
            'n_more_than_one': n_subs_more_than_one
        })
        return context


class YouTubeExampleReport(YouTubeReportIndividual, TemplateView):
    """Generates an individual report based on synthetic YouTube usage data."""

    template_name = 'reports/youtube/example_report.html'

    def register_classroom(self):
        """Register classroom object."""
        self.classroom = None

    def register_project(self):
        """Register project object."""
        self.project = None

    def check_classroom_active(self):
        return True

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
        context['expiration_date'] = 'This example report does not expire'
        context['class_id'] = '1234567890'
        context['class_name'] = 'Example class'
        return context

    def get_context_data(self, **kwargs):
        context = {}

        # Generate synthetic data.
        start_date = timezone.now().date() - timedelta(days=5)
        wh_data = generate_synthetic_watch_history(start_date)
        sh_data = generate_synthetic_search_history(start_date)

        # Add watch history (wh) data to context.
        context.update(
            self.get_watch_context(wh_data['data'], is_example=True)
        )

        # Add search history (sh) data to context.
        context.update(
            self.get_search_context(sh_data['data'], is_example=True)
        )

        return context
