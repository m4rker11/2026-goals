"""Google Calendar OAuth authentication."""

import sys
from pathlib import Path

from .calendar_service import TOKEN_DIR, TOKEN_PATH, CREDENTIALS_PATH


def run_auth():
    """
    Run OAuth flow for Google Calendar.

    Requires credentials.json in ~/.goals-mcp/
    """
    # Ensure token directory exists
    TOKEN_DIR.mkdir(parents=True, exist_ok=True)

    if not CREDENTIALS_PATH.exists():
        print(f"""
Google Calendar credentials not found.

To set up:
1. Go to https://console.cloud.google.com/
2. Create a project (or use existing)
3. Enable Google Calendar API
4. Create OAuth 2.0 credentials (Desktop app)
5. Download credentials.json
6. Save to: {CREDENTIALS_PATH}

Then run: goals-mcp auth
""")
        sys.exit(1)

    try:
        from google_auth_oauthlib.flow import Flow
        import pickle
        import webbrowser

        SCOPES = ['https://www.googleapis.com/auth/calendar']

        from urllib.parse import urlparse, parse_qs

        # Use localhost redirect, but user will paste the URL manually
        flow = Flow.from_client_secrets_file(
            str(CREDENTIALS_PATH),
            scopes=SCOPES,
            redirect_uri='http://localhost:8080/'
        )

        auth_url, _ = flow.authorization_url(access_type='offline', prompt='consent')

        print("Opening browser for Google sign-in...")
        print(f"\nIf browser doesn't open, visit:\n{auth_url}\n")
        webbrowser.open(auth_url)

        print("After authorizing, you'll be redirected to a page that won't load.")
        print("Copy the FULL URL from your browser's address bar and paste it here.\n")

        redirect_url = input("Paste the redirect URL: ").strip()

        # Parse code from URL
        parsed = urlparse(redirect_url)
        params = parse_qs(parsed.query)
        if 'code' not in params:
            print("Error: No authorization code found in URL")
            sys.exit(1)

        code = params['code'][0]
        flow.fetch_token(code=code)
        creds = flow.credentials

        # Save credentials in pickle format for gcsa
        with open(TOKEN_PATH, 'wb') as f:
            pickle.dump(creds, f)

        from gcsa.google_calendar import GoogleCalendar
        gc = GoogleCalendar(
            credentials_path=str(CREDENTIALS_PATH),
            token_path=str(TOKEN_PATH),
        )

        print(f"✓ Authorized. Token saved to {TOKEN_PATH}")
        print()

        # List available calendars
        print("Calendars found:")
        try:
            for cal in gc.get_calendar_list():
                primary = "(primary)" if cal.primary else ""
                access = "✓" if cal.access_role in ("owner", "writer") else "(read-only)"
                print(f"  • {cal.summary} {primary} {access}")
        except Exception as e:
            print(f"  (Could not list calendars: {e})")

    except Exception as e:
        print(f"Authentication failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    run_auth()
