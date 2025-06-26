# Digital Meal Portability

This sub-application is used to connect Digital Meal with portability APIs of external platforms (e.g., TikTok).

## Development

### Prerequisits

- A TikTok Developer account with a sandbox project
- ngrok installed to gate the response retrieved from TikTok to the locally hosted application

### How-To

1. Start an ngrok connection in a PowerShell: `ngrok http 8000 --url https://eager-mayfly-united.ngrok-free.app`
2. Run the Django development server

This setup will forward the traffic received by ngrok to the locally hosted application.


## TikTok

### Authentication Flow

- Send User to Login Page
- Receive authorization code from TikTok
- Get access token from TikTok with authorization code
