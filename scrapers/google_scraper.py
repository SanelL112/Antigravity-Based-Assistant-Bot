import os
import logging
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

os.environ['OAUTHLIB_RELAX_TOKEN_SCOPE'] = '1'

logger = logging.getLogger(__name__)

# If modifying these scopes, delete the file token.json.
SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/classroom.courses.readonly',
    'https://www.googleapis.com/auth/classroom.coursework.me.readonly',
    'https://www.googleapis.com/auth/classroom.announcements.readonly'
]

CREDENTIALS_PATH = os.path.join(os.path.dirname(__file__), '..', 'credentials.json')
TOKEN_PATH = os.path.join(os.path.dirname(__file__), '..', 'token.json')

def get_google_credentials():
    creds = None
    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as e:
                logger.error(f"Failed to refresh token: {e}")
                creds = None
                
        if not creds:
            if not os.path.exists(CREDENTIALS_PATH):
                logger.error("credentials.json not found! You must download it from Google Cloud Console.")
                return None
            try:
                # Note: On a remote headless server, run_local_server might not work directly. 
                # You may need to run this script locally first, then upload the token.json.
                flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
                creds = flow.run_local_server(port=0, open_browser=False)
            except Exception as e:
                logger.error(f"Failed to authenticate: {e}")
                return None
            
        with open(TOKEN_PATH, 'w') as token:
            token.write(creds.to_json())
            
    return creds

def get_unread_emails(limit=5):
    """Fetch recent unread emails from Gmail."""
    creds = get_google_credentials()
    if not creds:
        return "Google API credentials not configured. Please place credentials.json in the project root."
        
    try:
        service = build('gmail', 'v1', credentials=creds)
        # Call the Gmail API
        results = service.users().messages().list(userId='me', labelIds=['UNREAD'], maxResults=limit).execute()
        messages = results.get('messages', [])

        if not messages:
            return "No unread emails."
            
        result = ["📧 **Recent Unread Emails:**"]
        for msg in messages:
            msg_data = service.users().messages().get(userId='me', id=msg['id'], format='metadata', metadataHeaders=['Subject', 'From']).execute()
            headers = msg_data['payload']['headers']
            subject = next((header['value'] for header in headers if header['name'] == 'Subject'), 'No Subject')
            sender = next((header['value'] for header in headers if header['name'] == 'From'), 'Unknown Sender')
            result.append(f"From: {sender}\nSubject: {subject}\n")
            
        return "\n".join(result)
    except Exception as e:
        logger.error(f"Error fetching Gmail: {e}")
        return f"Error connecting to Gmail: {e}"

def get_classroom_assignments():
    """Fetch coursework from Google Classroom."""
    creds = get_google_credentials()
    if not creds:
        return "Google API credentials not configured."
        
    try:
        service = build('classroom', 'v1', credentials=creds)
        # Call the Classroom API
        results = service.courses().list(courseStates=['ACTIVE']).execute()
        courses = results.get('courses', [])

        if not courses:
            return "No active Google Classroom courses found."
            
        result = ["🏫 **Google Classroom Assignments:**"]
        for course in courses:
            try:
                coursework = service.courses().courseWork().list(courseId=course['id'], courseWorkStates=['PUBLISHED']).execute()
                works = coursework.get('courseWork', [])
                for work in works:
                    title = work.get('title', 'Untitled')
                    result.append(f"[{course['name']}] {title}")
            except Exception as e:
                logger.warning(f"Could not fetch coursework for {course['name']}: {e}")
                
        if len(result) == 1:
             return "No published coursework found."
             
        return "\n".join(result)
    except Exception as e:
        logger.error(f"Error fetching Classroom data: {e}")
        return f"Error connecting to Google Classroom: {e}"


def get_classroom_announcements(limit=10):
    """Fetch recent announcements from all active Google Classroom courses."""
    creds = get_google_credentials()
    if not creds:
        return "Google API credentials not configured."

    try:
        service = build('classroom', 'v1', credentials=creds)
        results = service.courses().list(courseStates=['ACTIVE']).execute()
        courses = results.get('courses', [])

        if not courses:
            return "No active Google Classroom courses found."

        result = ["📢 **Google Classroom Announcements:**"]
        for course in courses:
            try:
                announcements = service.courses().announcements().list(
                    courseId=course['id'],
                    announcementStates=['PUBLISHED'],
                    pageSize=limit
                ).execute()
                items = announcements.get('announcements', [])
                for item in items:
                    text = item.get('text', '(no text)').replace('\n', ' ').strip()
                    if len(text) > 200:
                        text = text[:200] + '...'
                    result.append(f"[{course['name']}] {text}")
            except Exception as e:
                logger.warning(f"Could not fetch announcements for {course['name']}: {e}")

        if len(result) == 1:
            return "No recent Classroom announcements found."

        return "\n".join(result)
    except Exception as e:
        logger.error(f"Error fetching Classroom announcements: {e}")
        return f"Error connecting to Google Classroom: {e}"

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("Testing Gmail API...")
    print(get_unread_emails())
    print("\nTesting Google Classroom Assignments...")
    print(get_classroom_assignments())
    print("\nTesting Google Classroom Announcements...")
    print(get_classroom_announcements())
