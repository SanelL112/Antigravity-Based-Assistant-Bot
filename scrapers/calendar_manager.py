import os
import datetime
from googleapiclient.discovery import build
from scrapers.google_scraper import get_google_credentials

def add_study_session(summary: str, start_time_iso: str, duration_minutes: int) -> str:
    """Adds a study session to the user's primary Google Calendar."""
    try:
        creds = get_google_credentials()
        service = build('calendar', 'v3', credentials=creds)

        start_time = datetime.datetime.fromisoformat(start_time_iso)
        end_time = start_time + datetime.timedelta(minutes=int(duration_minutes))

        event = {
            'summary': f"📚 Study Session: {summary}",
            'description': 'Automatically scheduled study session via TaskBot.',
            'start': {
                'dateTime': start_time.isoformat(),
                'timeZone': 'America/New_York', # Assuming EST based on user's local time metadata
            },
            'end': {
                'dateTime': end_time.isoformat(),
                'timeZone': 'America/New_York',
            },
            'reminders': {
                'useDefault': False,
                'overrides': [
                    {'method': 'popup', 'minutes': 30},
                ],
            },
        }

        event = service.events().insert(calendarId='primary', body=event).execute()
        return f"Successfully scheduled '{summary}' for {duration_minutes} mins on {start_time.strftime('%b %d at %I:%M %p')}. Event Link: {event.get('htmlLink')}"
    except Exception as e:
        return f"Failed to schedule study session: {e}"

if __name__ == "__main__":
    # Test block
    print(add_study_session("Test Assignment", (datetime.datetime.now() + datetime.timedelta(hours=1)).isoformat(), 60))
