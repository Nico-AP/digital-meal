from django.contrib import admin
from .models import OAuthStateToken, TikTokAccessToken, TikTokDataRequest

@admin.register(OAuthStateToken)
class OAuthStateTokenAdmin(admin.ModelAdmin):
    list_display = ['token', 'created_at', 'used', 'is_expired']
    list_filter = ['used', 'created_at']
    readonly_fields = ['token', 'created_at']

@admin.register(TikTokAccessToken)
class TikTokAccessTokenAdmin(admin.ModelAdmin):
    list_display = [
        'open_id',
        'created_at',
        'token_expiration_date',
        'is_expired'
    ]
    search_fields = ['open_id']
    readonly_fields = ['token', 'refresh_token', 'created_at']

    def is_expired(self, obj):
        return obj.is_expired()

    is_expired.boolean = True

@admin.register(TikTokDataRequest)
class TikTokDataRequestAdmin(admin.ModelAdmin):
    list_display = [
        'open_id',
        'request_id',
        'status',
        'issued_at',
        'downloaded_at',
        'download_attempted',
        'download_succeeded'
    ]
    list_filter = [
        'status',
        'downloaded_at',
        'issued_at',
        'download_attempted',
        'download_succeeded'
    ]
    search_fields = ['open_id', 'request_id']
