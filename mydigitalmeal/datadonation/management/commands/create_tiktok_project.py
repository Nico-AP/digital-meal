import logging

from ddm.datadonation.models import (
    BlueprintFilePath,
    DonationBlueprint,
    ExtractionField,
    FileUploader,
)
from ddm.projects.models import DonationProject, ResearchProfile
from django.contrib.auth import get_user_model
from django.core.management import BaseCommand, CommandError

from mydigitalmeal.datadonation.constants import TIKTOK_PROJECT_SLUG

logger = logging.getLogger(__name__)

User = get_user_model()


PROJECT_CONFIG = {
    "name": "TikTok",
    "contact_information": "",
    "data_protection_statement": "",
    "slug": TIKTOK_PROJECT_SLUG,
    "briefing_text": "",
    "briefing_consent_enabled": False,
    "briefing_consent_label_yes": "Ja",
    "briefing_consent_label_no": "Nein",
    "debriefing_text": "",
    "super_secret": False,
    "redirect_enabled": False,
    "redirect_target": "",
    "url_parameter_enabled": True,
    "expected_url_parameters": "class",
    "active": True,
}

FILE_UPLOADER_CONFIG = {
    "name": "TikTok",
    "upload_type": "zip file",
    "combined_consent": True,
}

BLUEPRINT_CONFIGS = [
    {
        "name": "Angesehene Videos",
        "description": "Videos, die du dir angesehen hast.",
        "display_position": 1,
        "exp_file_format": "json",
        "parser_config": {
            "format": "json",
            "nested_loop_path": "",
            "array_join_separator": "\n",
            "extraction_root": "Your Activity.Watch History.VideoList",
            "max_root_entries": None,
        },
        "expected_fields": '"Date", "Link"',
        "expected_fields_regex_matching": False,
        "blueprint_filepaths": [
            {"path": "user_data_tiktok\\.json", "is_regex": True, "priority": 1}
        ],
        "extraction_fields": [
            {
                "expected_name": "Date",
                "match_regex": False,
                "keep_in_donation": True,
            },
            {
                "expected_name": "Link",
                "match_regex": False,
                "keep_in_donation": True,
            },
        ],
        "processing_rules": [],
    },
    {
        "name": "Gepostete Videos",
        "description": "Informationen, wann und mit welchen Einstellungen du "
        "Videos gepostet hast. Der Link und der Titel des Videos "
        "wird nicht ausgelesen.",
        "display_position": 1,
        "exp_file_format": "json",
        "parser_config": {
            "format": "json",
            "nested_loop_path": "",
            "array_join_separator": "\n",
            "extraction_root": "Post.Posts.VideoList",
            "max_root_entries": None,
        },
        "expected_fields": '"Date", "Link"',
        "expected_fields_regex_matching": False,
        "blueprint_filepaths": [
            {"path": "user_data_tiktok\\.json", "is_regex": True, "priority": 1}
        ],
        "extraction_fields": [
            {
                "expected_name": "Date",
                "match_regex": False,
                "keep_in_donation": True,
            },
            {
                "expected_name": "WhoCanView",
                "match_regex": False,
                "keep_in_donation": True,
            },
            {
                "expected_name": "AllowComments",
                "match_regex": False,
                "keep_in_donation": True,
            },
            {
                "expected_name": "AllowStitches",
                "match_regex": False,
                "keep_in_donation": True,
            },
            {
                "expected_name": "AllowDuets",
                "match_regex": False,
                "keep_in_donation": True,
            },
            {
                "expected_name": "AllowSharingToStory",
                "match_regex": False,
                "keep_in_donation": True,
            },
            {
                "expected_name": "ContentDisclosure",
                "match_regex": False,
                "keep_in_donation": True,
            },
            {
                "expected_name": "AIGeneratedContent",
                "match_regex": False,
                "keep_in_donation": True,
            },
            {
                "expected_name": "Sound",
                "match_regex": False,
                "keep_in_donation": True,
            },
        ],
        "processing_rules": [],
    },
    {
        "name": "Aktivitätszusammenfassung",
        "description": "Anzahl der Videos, die du kommentiert, geteilt und "
        "angesehen hast.",
        "display_position": 1,
        "exp_file_format": "json",
        "parser_config": {
            "format": "json",
            "nested_loop_path": "",
            "array_join_separator": "\n",
            "extraction_root": "Your Activity.Activity Summary.ActivitySummaryMap",
            "max_root_entries": None,
        },
        "expected_fields": '"videosWatchedToTheEndSinceAccountRegistration"',
        "expected_fields_regex_matching": False,
        "blueprint_filepaths": [
            {"path": "user_data_tiktok\\.json", "is_regex": True, "priority": 1}
        ],
        "extraction_fields": [
            {
                "expected_name": "videosCommentedOnSinceAccountRegistration",
                "match_regex": False,
                "keep_in_donation": True,
            },
            {
                "expected_name": "videosSharedSinceAccountRegistration",
                "match_regex": False,
                "keep_in_donation": True,
            },
            {
                "expected_name": "videosSharedSinceAccountRegistration",
                "match_regex": False,
                "keep_in_donation": True,
            },
        ],
        "processing_rules": [],
    },
    {
        "name": "Effekt-Bookmarks",
        "description": "Effekte, die du gespeichert hast.",
        "display_position": 1,
        "exp_file_format": "json",
        "parser_config": {
            "format": "json",
            "nested_loop_path": "",
            "array_join_separator": "\n",
            "extraction_root": "Your Activity.Favorite Effects.FavoriteEffectsList",
            "max_root_entries": None,
        },
        "expected_fields": '"EffectLink"',
        "expected_fields_regex_matching": False,
        "blueprint_filepaths": [
            {"path": "user_data_tiktok\\.json", "is_regex": True, "priority": 1}
        ],
        "extraction_fields": [
            {
                "expected_name": "Date",
                "match_regex": False,
                "keep_in_donation": True,
            },
            {
                "expected_name": "EffectLink",
                "match_regex": False,
                "keep_in_donation": True,
            },
        ],
        "processing_rules": [],
    },
    {
        "name": "Hashtag-Bookmarks",
        "description": "Hashtags, die du gespeichert hast.",
        "display_position": 1,
        "exp_file_format": "json",
        "parser_config": {
            "format": "json",
            "nested_loop_path": "",
            "array_join_separator": "\n",
            "extraction_root": "Your Activity.Favorite Hashtags.FavoriteHashtagList",
            "max_root_entries": None,
        },
        "expected_fields": '"Date"',
        "expected_fields_regex_matching": False,
        "blueprint_filepaths": [
            {"path": "user_data_tiktok\\.json", "is_regex": True, "priority": 1}
        ],
        "extraction_fields": [
            {
                "expected_name": "Date",
                "match_regex": False,
                "keep_in_donation": True,
            },
            {
                "expected_name": "(L|l)ink",
                "match_regex": True,
                "keep_in_donation": True,
                "alias": "link",
            },
        ],
        "processing_rules": [],
    },
    {
        "name": "Video-Bookmarks",
        "description": "Videos, die du gespeichert hast.",
        "display_position": 1,
        "exp_file_format": "json",
        "parser_config": {
            "format": "json",
            "nested_loop_path": "",
            "array_join_separator": "\n",
            "extraction_root": "Your Activity.Favorite Videos.FavoriteVideoList",
            "max_root_entries": None,
        },
        "expected_fields": '"Date"',
        "expected_fields_regex_matching": False,
        "blueprint_filepaths": [
            {"path": "user_data_tiktok\\.json", "is_regex": True, "priority": 1}
        ],
        "extraction_fields": [
            {
                "expected_name": "Date",
                "match_regex": False,
                "keep_in_donation": True,
            },
            {
                "expected_name": "(L|l)ink",
                "match_regex": True,
                "keep_in_donation": True,
                "alias": "link",
            },
        ],
        "processing_rules": [],
    },
    {
        "name": "Sound-Bookmarks",
        "description": "Sounds, die du gespeichert hast.",
        "display_position": 1,
        "exp_file_format": "json",
        "parser_config": {
            "format": "json",
            "nested_loop_path": "",
            "array_join_separator": "\n",
            "extraction_root": "Your Activity.Favorite Sounds.FavoriteSoundList",
            "max_root_entries": None,
        },
        "expected_fields": '"Date"',
        "expected_fields_regex_matching": False,
        "blueprint_filepaths": [
            {"path": "user_data_tiktok\\.json", "is_regex": True, "priority": 1}
        ],
        "extraction_fields": [
            {
                "expected_name": "Date",
                "match_regex": False,
                "keep_in_donation": True,
            },
            {
                "expected_name": "(L|l)ink",
                "match_regex": True,
                "keep_in_donation": True,
                "alias": "link",
            },
        ],
        "processing_rules": [],
    },
    {
        "name": "Gefolgte Accounts",
        "description": "Accounts, denen du folgst.",
        "display_position": 1,
        "exp_file_format": "json",
        "parser_config": {
            "format": "json",
            "nested_loop_path": "",
            "array_join_separator": "\n",
            "extraction_root": "Your Activity.Following.Following",
            "max_root_entries": None,
        },
        "expected_fields": '"Date", "UserName"',
        "expected_fields_regex_matching": False,
        "blueprint_filepaths": [
            {"path": "user_data_tiktok\\.json", "is_regex": True, "priority": 1}
        ],
        "extraction_fields": [
            {
                "expected_name": "Date",
                "match_regex": False,
                "keep_in_donation": True,
            },
            {
                "expected_name": "UserName",
                "match_regex": False,
                "keep_in_donation": True,
            },
        ],
        "processing_rules": [],
    },
    {
        "name": "Gelikte Videos",
        "description": "Videos, die du geliked hast.",
        "display_position": 1,
        "exp_file_format": "json",
        "parser_config": {
            "format": "json",
            "nested_loop_path": "",
            "array_join_separator": "\n",
            "extraction_root": "Your Activity.Like List.ItemFavoriteList",
            "max_root_entries": None,
        },
        "expected_fields": '"(D|d)ate"',
        "expected_fields_regex_matching": True,
        "blueprint_filepaths": [
            {"path": "user_data_tiktok\\.json", "is_regex": True, "priority": 1}
        ],
        "extraction_fields": [
            {
                "expected_name": "(D|d)ate",
                "match_regex": True,
                "keep_in_donation": True,
                "alias": "date",
            },
            {
                "expected_name": "(L|l)ink",
                "match_regex": True,
                "keep_in_donation": True,
                "alias": "link",
            },
        ],
        "processing_rules": [],
    },
    {
        "name": "Durchgeführte Suchen",
        "description": "Die Begriffe, nach denen du gesucht hast.",
        "display_position": 1,
        "exp_file_format": "json",
        "parser_config": {
            "format": "json",
            "nested_loop_path": "",
            "array_join_separator": "\n",
            "extraction_root": "Your Activity.Searches.SearchList",
            "max_root_entries": None,
        },
        "expected_fields": '"Date"',
        "expected_fields_regex_matching": False,
        "blueprint_filepaths": [
            {"path": "user_data_tiktok\\.json", "is_regex": True, "priority": 1}
        ],
        "extraction_fields": [
            {
                "expected_name": "(D|d)ate",
                "match_regex": True,
                "keep_in_donation": True,
                "alias": "date",
            },
            {
                "expected_name": "SearchTerm",
                "match_regex": False,
                "keep_in_donation": True,
            },
        ],
        "processing_rules": [],
    },
    {
        "name": "Kommentare (nur Zeitpunkt)",
        "description": "Zeitpunkte, an denen du einen Kommentar hinterlassen "
        "hast. Der Inhalt der Kommentare wird nicht ausgelesen.",
        "display_position": 1,
        "exp_file_format": "json",
        "parser_config": {
            "format": "json",
            "nested_loop_path": "",
            "array_join_separator": "\n",
            "extraction_root": "Comment.Comments.CommentsList",
            "max_root_entries": None,
        },
        "expected_fields": '"comment"',
        "expected_fields_regex_matching": False,
        "blueprint_filepaths": [
            {"path": "user_data_tiktok\\.json", "is_regex": True, "priority": 1}
        ],
        "extraction_fields": [
            {
                "expected_name": "(D|d)ate",
                "match_regex": True,
                "keep_in_donation": True,
                "alias": "date",
            },
        ],
        "processing_rules": [],
    },
    {
        "name": "Geteilte Videos",
        "description": "Informationen zu den Videos, die du mit anderen geteilt hast.",
        "display_position": 1,
        "exp_file_format": "json",
        "parser_config": {
            "format": "json",
            "nested_loop_path": "",
            "array_join_separator": "\n",
            "extraction_root": "Your Activity.Share History.ShareHistoryList",
            "max_root_entries": None,
        },
        "expected_fields": '"Date", "SharedContent"',
        "expected_fields_regex_matching": False,
        "blueprint_filepaths": [
            {"path": "user_data_tiktok\\.json", "is_regex": True, "priority": 1}
        ],
        "extraction_fields": [
            {
                "expected_name": "(D|d)ate",
                "match_regex": True,
                "keep_in_donation": True,
                "alias": "date",
            },
            {
                "expected_name": "SharedContent",
                "match_regex": False,
                "keep_in_donation": True,
            },
            {
                "expected_name": "Method",
                "match_regex": False,
                "keep_in_donation": True,
            },
            {
                "expected_name": "(L|l)ink",
                "match_regex": True,
                "keep_in_donation": True,
                "alias": "link",
            },
        ],
        "processing_rules": [],
    },
]


class Command(BaseCommand):
    help = "Creates a DDM project to collect TikTok donations."

    def add_arguments(self, parser):
        parser.add_argument("user_id", type=int)

    def handle(self, *args, **options):
        user_id = options["user_id"]

        # Try to get user
        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist as e:
            msg = f"User with ID {user_id} not found"
            raise CommandError(msg) from e

        # Check if project already exists
        if DonationProject.objects.filter(slug=TIKTOK_PROJECT_SLUG).exists():
            self.stdout.write(
                self.style.NOTICE(
                    f"DDM project with URL ID '{TIKTOK_PROJECT_SLUG}' already exists",
                ),
            )
            return

        # Get or create research profile
        owner_profile, _ = ResearchProfile.objects.get_or_create(user=user)

        # Create Project
        project = DonationProject.objects.create(
            owner=owner_profile,
            **PROJECT_CONFIG,
        )

        # Create Uploader
        uploader = FileUploader.objects.create(
            project=project,
            **FILE_UPLOADER_CONFIG,
        )

        # Create Blueprints
        for config in BLUEPRINT_CONFIGS:
            excluded_fields = [
                "processing_rules",
                "blueprint_filepaths",
                "extraction_fields",
            ]
            bp_config = {i: config[i] for i in config if i not in excluded_fields}
            blueprint = DonationBlueprint.objects.create(
                project=project,
                file_uploader=uploader,
                **bp_config,
            )

            # Create filepaths
            for fp in config["blueprint_filepaths"]:
                BlueprintFilePath.objects.create(
                    blueprint=blueprint,
                    **fp,
                )

            # Create extraction fields
            for ef in config["extraction_fields"]:
                ExtractionField.objects.create(
                    blueprint=blueprint,
                    **ef,
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"DDM project with URL ID '{TIKTOK_PROJECT_SLUG}' successfully created",
            ),
        )
