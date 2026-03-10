import logging
import random

from django.http import Http404
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import TemplateView

from mydigitalmeal.profiles.mixins import LoginAndProfileRequiredMixin
from mydigitalmeal.reports.utils import get_tiktok_video_metadata
from mydigitalmeal.statistics.models import StatisticsRequest, StatisticsScope
from mydigitalmeal.userflow.constants import URLShortcut
from mydigitalmeal.userflow.sessions import AddUserflowSessionMixin

logger = logging.getLogger(__name__)


class MainReportView(LoginAndProfileRequiredMixin, TemplateView):
    template_name = "reports/tiktok/report.html"
    login_url = reverse_lazy(URLShortcut.LOGIN)


class StatisticsView(
    LoginAndProfileRequiredMixin, AddUserflowSessionMixin, TemplateView
):
    template_name = "reports/tiktok/partials/_combined_statistics.html"
    session_invalid_redirect = URLShortcut.OVERVIEW
    statistics_request: StatisticsRequest | None = None

    def validate_userflow_session(self, request, *args, **kwargs):
        """Redirect to entry view if no statistics request ID in session"""
        session = self.userflow_session.get()
        if not session.statistics_requested or session.request_id is None:
            return redirect(self.session_invalid_redirect)

        return None

    def get(self, request, *args, **kwargs):
        session = self.userflow_session.get()
        try:
            self.statistics_request = StatisticsRequest.objects.get(
                public_id=session.request_id
            )
        except StatisticsRequest.DoesNotExist:
            logger.warning(
                "StatisticsRequest with ID %s from userflow session not found",
                session.request_id,
            )
            return redirect(self.session_invalid_redirect)

        if self.statistics_request.has_failed():
            # Statistics computation failed
            # TODO: Handle this better
            msg = "Statistics could not be computed"
            raise Http404(msg)
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["statistics_ready"] = False
        if not self.statistics_request.is_ready():
            # Waiting for statistics request to complete
            return context

        self._stats = self.load_statistics()

        if self._stats is None:
            # TODO: Optimize this
            msg = "Something went wrong - report could not be generated"
            raise Http404(msg)

        context |= self._get_video_viewed_stats()
        context |= self._get_daily_routine_stats()
        context |= self._get_usage_session_scrolling()
        context |= self._get_top_video()
        context |= self._get_peak_day()
        context |= self._get_usage_session_general()

        context["statistics_ready"] = True

        return context

    def load_statistics(self):
        return (
            self.statistics_request.get_statistics()
            .filter(scope=StatisticsScope.INTERVAL)
            .first()
        )

    def not_all_stats_none(self, d: dict) -> bool:
        return any(s is not None for s in d.values())

    def _get_video_viewed_stats(self) -> dict:
        """For "reports/tiktok/partials/_video_viewed_stats.html" template"""
        stats = {
            "videos_total": self._stats.total_videos,
            "videos_per_day": self._stats.videos_per_day,
        }
        stats.update({"video_viewed_stats_available": self.not_all_stats_none(stats)})
        return stats

    def _get_daily_routine_stats(self) -> dict:
        """For "reports/tiktok/partials/_daily_routine.html" template"""
        hour_start = self._stats.peak_hour
        hour_start = 0 if hour_start == 24 else hour_start  # noqa: PLR2004
        hour_end = hour_start + 1 if hour_start is not None else None

        stats = {
            "routine_start_hour": hour_start,
            "routine_end_hour": hour_end,
        }
        stats.update({"daily_routine_available": self.not_all_stats_none(stats)})
        return stats

    def _get_usage_session_scrolling(self) -> dict:
        """For "reports/tiktok/partials/_usage_session_scrolling.html" template"""
        stats = {
            "scroll_threshold_pct": self._stats.scroll_threshold_pct,
            "scroll_threshold_sec": self._stats.scroll_threshold_sec,
        }
        stats.update(
            {"usage_session_scrolling_available": self.not_all_stats_none(stats)}
        )
        return stats

    def _get_top_video(self) -> dict:
        """For "reports/tiktok/partials/_top_video.html" template"""
        video_metadata = get_tiktok_video_metadata(self._stats.top_video_id)
        # TODO: Fallback when video does not exist;
        #  currently, this report part will just be skipped
        stats = {
            "top_video_thumbnail_url": video_metadata.get("thumbnail"),
            "top_video_seen_count": self._stats.top_video_seen_count,
            "top_video_last_seen_date": self._stats.top_video_last_seen_date,
        }

        stats.update({"top_video_available": self.not_all_stats_none(stats)})
        return stats

    def _get_peak_day(self) -> dict:
        """For "reports/tiktok/partials/_peak_day.html" template"""

        def generate_guess_options(correct: int, n_options: int = 3) -> dict[int, bool]:
            options = {
                correct: True,
            }

            # Prepare options depending on correct value
            if correct == 1:
                options[0] = False
                multiplier_min = 2
                multiplier_max = 10

            elif correct < 10:  # noqa: PLR2004
                multiplier_min = 0.3
                multiplier_max = 6

            else:
                multiplier_min = 0.5
                multiplier_max = 1.5

            # Generate options for larger correct number
            base_value = correct if correct > 0 else 1
            while (
                len(options) < n_options and len(options) <= base_value * multiplier_max
            ):
                multiplier = random.uniform(multiplier_min, multiplier_max)  # noqa: S311
                guess = round(base_value * multiplier)
                if guess not in options and guess > 0:
                    options[guess] = False

            return dict(sorted(options.items(), key=lambda item: item[0]))

        video_count = self._stats.peak_day_video_count
        stats = {
            "peak_day_date": self._stats.peak_day_date,
            "peak_day_video_count": video_count,
        }

        stats_available = self.not_all_stats_none(stats)

        if stats_available and video_count is not None:
            peak_guesses = generate_guess_options(video_count)
        else:
            peak_guesses = None

        stats.update(
            {
                "peak_day_available": self.not_all_stats_none(stats),
                "peak_guesses": peak_guesses,
            }
        )
        return stats

    def _get_usage_session_general(self) -> dict:
        """For "reports/tiktok/partials/_usage_session_general.html" template"""
        stats = {
            "usage_session_n_days": self._stats.total_days_with_activity,
            "usage_session_minutes_mean": self._stats.avg_session_duration_seconds,
            "usage_session_videos_mean": self._stats.avg_videos_per_session,
        }

        stats.update(
            {"usage_session_general_available": self.not_all_stats_none(stats)}
        )

        """
        TODO: Still needs to be implemented
        from mydigitalmeal.reports.utils import generate_usage_session_image
        d = {
            "usage_session_image_a": "TODO",
            "usage_session_image_days_highlighted": "TODO",
        }
        """

        return stats
