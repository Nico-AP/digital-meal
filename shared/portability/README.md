# Digital Meal Portability

This sub-application is used to connect Digital Meal with portability APIs of external platforms (e.g., TikTok).

## Development

### Prerequisites

- A TikTok Developer account with a sandbox project
- ngrok installed to gate the response retrieved from TikTok to the locally hosted application

### How-To

1. Start a ngrok connection in a PowerShell: `ngrok http 8000 --url https://eager-mayfly-united.ngrok-free.app`
2. Run the Django development server

This setup will forward the traffic received by ngrok to the locally hosted application.


## TikTok

### Authentication Flow

- Send User to Login Page
- Receive authorization code from TikTok
- Get access token from TikTok with authorization code

### Settings and Environment Variables

To integrate the portability module in a Django application, the following settings must be defined in the
settings/environment variables:

- TIKTOK_AUTH_URL: Link to TikTok's authorization page (optional; defaults to 'https://www.tiktok.com/v2/auth/authorize/')
- TIKTOK_TOKEN_URL: Link to TikTok's User Access Management API (optional; defaults to 'https://open.tiktokapis.com/v2/oauth/token/')
- TIKTOK_USER_INFO_URL: Link to TikTok's User Info API (optional; defaults to 'https://open.tiktokapis.com/v2/user/info/')
- TIKTOK_CLIENT_KEY: The client key issued by TikTok
- TIKTOK_CLIENT_SECRET: The client secret issued by TikTok
- TIKTOK_REDIRECT_URL: The callback URL to which TikTok should redirect users (must point to https://<domain.com>/portability/tiktok/auth/)
