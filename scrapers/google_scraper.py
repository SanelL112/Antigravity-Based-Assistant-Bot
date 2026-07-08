import os
import logging
import warnings
import time as _time
import threading
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from config import TOKEN_PATH, CREDENTIALS_PATH

os.environ['OAUTHLIB_RELAX_TOKEN_SCOPE'] = '1'
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '0'

# ── Cached credentials (avoid re-reading token.json on every call) ────────────
_google_creds = None
_google_creds_refreshed_at = 0
# Lock to prevent race conditions in token refresh
_creds_lock = threading.Lock()

CREDS = TOKEN_PATH  # alias for backward compatibility
# Suppress the "Not all requested scopes were granted" oauthlib warning —
# the token has all needed scopes; the warning fires because Google's auth
# library logs it at WARNING level on every credential load.
warnings.filterwarnings('ignore', message='.*Not all requested scopes.*')
logging.getLogger('google_auth_oauthlib').setLevel(logging.ERROR)
logging.getLogger('google.auth').setLevel(logging.ERROR)

logger = logging.getLogger(__name__)

# If modifying these scopes, delete the file token.json.
SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/classroom.courses.readonly',
    'https://www.googleapis.com/auth/classroom.coursework.me.readonly',
    'https://www.googleapis.com/auth/classroom.announcements.readonly',
    'https://www.googleapis.com/auth/documents.readonly',
    'https://www.googleapis.com/auth/drive.readonly',
    'https://www.googleapis.com/auth/calendar.events'
]

CREDENTIALS_PATH = os.path.join(os.path.dirname(__file__), '..', 'credentials.json')
TOKEN_PATH = os.path.join(os.path.dirname(__file__), '..', 'token.json')

def get_google_credentials():
    """Get Google credentials with caching and retry on refresh.
    
    Thread-safe: uses _creds_lock to prevent concurrent refreshes.
    """
    global _google_creds, _google_creds_refreshed_at

    # Fast path: return cached creds if still valid (cache for 5 minutes)
    # This check is outside the lock for performance - stale check is OK
    if _google_creds and _google_creds.valid and (_time.time() - _google_creds_refreshed_at) < 300:
        return _google_creds

    # Slow path: need to refresh or re-authenticate - use lock
    with _creds_lock:
        # Re-check inside lock (double-checked locking pattern)
        if _google_creds and _google_creds.valid and (_time.time() - _google_creds_refreshed_at) < 300:
            return _google_creds

        creds = None
        if os.path.exists(TOKEN_PATH):
            creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                # Retry refresh up to 3 times with backoff
                for attempt in range(3):
                    try:
                        creds.refresh(Request())
                        break
                    except Exception as e:
                        if attempt < 2:
                            _time.sleep(2 ** attempt)
                        else:
                            logger.error(f"Failed to refresh token after 3 attempts: {e}")
                            creds = None
            
            if not creds or not creds.valid:
                # Token missing or scopes changed — re-authenticate via local server flow
                logger.info("Re-authenticating with Google (local server flow)...")
                flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
                creds = flow.run_local_server(host='127.0.0.1', port=8080, prompt='consent', open_browser=False)
                with open(TOKEN_PATH, 'w') as token_file:
                    token_file.write(creds.to_json())
                logger.info("Google authentication successful with new scopes.")

        if not creds:
            logger.error("Token is missing or failed to refresh.")
            return None

        with open(TOKEN_PATH, 'w') as token:
            token.write(creds.to_json())

        _google_creds = creds
        _google_creds_refreshed_at = _time.time()
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
        
        import datetime
        cutoff = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=30)

        result = ["🏫 **Google Classroom Assignments:**"]
        for course in courses:
            try:
                coursework = service.courses().courseWork().list(
                    courseId=course['id'],
                    courseWorkStates=['PUBLISHED'],
                    orderBy='updateTime desc',
                    pageSize=15
                ).execute()
                works = coursework.get('courseWork', [])
                for work in works:
                    title = work.get('title', 'Untitled')
                    
                    # Extract due date if present
                    due_date_obj = work.get('dueDate')
                    due_time_obj = work.get('dueTime', {})
                    due_str = "No due date"
                    if due_date_obj:
                        year = due_date_obj.get('year', 0)
                        month = due_date_obj.get('month', 0)
                        day = due_date_obj.get('day', 0)
                        if year and month and day:
                            due_str = f"{year}-{month:02d}-{day:02d}"
                            hours = due_time_obj.get('hours', 0)
                            minutes = due_time_obj.get('minutes', 0)
                            if hours or minutes:
                                due_str += f" {hours:02d}:{minutes:02d}"
                    
                    # Filter: skip assignments updated more than 30 days ago
                    update_time = work.get('updateTime', '')
                    if update_time:
                        try:
                            updated = datetime.datetime.fromisoformat(update_time.replace('Z', '+00:00'))
                            if updated < cutoff:  # aware vs aware
                                continue
                        except Exception:
                            pass
                    
                    materials = work.get('materials', [])
                    mat_list = []
                    for mat in materials:
                        if 'driveFile' in mat and 'driveFile' in mat['driveFile']:
                            df = mat['driveFile']['driveFile']
                            mat_list.append(f"📎 {df.get('title')} ({df.get('alternateLink')})")
                        elif 'link' in mat:
                            l = mat['link']
                            mat_list.append(f"🔗 {l.get('title')} ({l.get('url')})")
                        elif 'youtubeVideo' in mat:
                            y = mat['youtubeVideo']
                            mat_list.append(f"▶️ {y.get('title')} ({y.get('alternateLink')})")
                    
                    mat_str = "\n    ".join(mat_list) if mat_list else "No attachments"
                    result.append(f"[{course['name']}] {title} — Due: {due_str}\n    {mat_str}")
            except Exception as e:
                logger.warning(f"Could not fetch coursework for {course['name']}: {e}")
                
        if len(result) == 1:
             return "No recent published coursework found."
             
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

def get_recent_google_docs():
    """Fetches text from Google Docs modified in the last 4 hours."""
    creds = get_google_credentials()
    if not creds:
        return "Not authenticated."

    try:
        drive_service = build('drive', 'v3', credentials=creds, cache_discovery=False)
        docs_service = build('docs', 'v1', credentials=creds, cache_discovery=False)

        import datetime
        four_hours_ago = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=4)).isoformat().replace("+00:00", "Z")
        
        # Search for Google Docs modified in the last 4 hours
        query = f"mimeType='application/vnd.google-apps.document' and modifiedTime > '{four_hours_ago}' and trashed=false"
        # Add shared drive support to watchdog query
        results = drive_service.files().list(
            q=query, 
            fields="files(id, name)", 
            pageSize=10,
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
            corpora="allDrives"
        ).execute()
        items = results.get('files', [])

        if not items:
            return "No recently modified Google Docs found."

        output = ["Recent Google Docs:"]
        for item in items:
            doc_id = item['id']
            title = item['name']
            try:
                # Fetch the document content
                doc = docs_service.documents().get(documentId=doc_id).execute()
                text_content = ""
                for element in doc.get('body', {}).get('content', []):
                    if 'paragraph' in element:
                        for pe in element['paragraph']['elements']:
                            if 'textRun' in pe:
                                text_content += pe['textRun']['content']
                
                # Truncate if it's super long to save tokens
                text_content = text_content.strip()
                if len(text_content) > 1000:
                    text_content = text_content[:1000] + "\n...[truncated]"
                    
                output.append(f"--- Doc: {title} ---\n{text_content}\n")
            except Exception as e:
                logger.warning(f"Could not read doc {title}: {e}")

        return "\n".join(output)
    except Exception as e:
        logger.error(f"Error fetching Google Docs: {e}")
        return f"Error connecting to Google Drive/Docs: {e}"

def download_drive_file(file_id: str, output_path: str) -> bool:
    """Downloads a file from Google Drive by file ID. Automatically exports Google Docs/Workspace files."""
    from googleapiclient.http import MediaIoBaseDownload
    import io
    creds = get_google_credentials()
    if not creds:
        logger.error("No credentials available to download file.")
        return False
    try:
        service = build('drive', 'v3', credentials=creds)
        
        # 1. Get file metadata to check mimeType (must support shared drives)
        file_meta = service.files().get(fileId=file_id, fields="mimeType,name", supportsAllDrives=True).execute()
        mime_type = file_meta.get("mimeType", "")
        file_name = file_meta.get("name", "")
        
        # Google Workspace types that MUST be exported (cannot be downloaded directly)
        workspace_types = {
            "application/vnd.google-apps.document": "application/pdf",
            "application/vnd.google-apps.spreadsheet": "application/pdf",
            "application/vnd.google-apps.presentation": "application/pdf",
            "application/vnd.google-apps.drawing": "application/pdf",
            "application/vnd.google-apps.script": "application/vnd.google-apps.script+json",
            "application/vnd.google-apps.form": "application/pdf",
            "application/vnd.google-apps.site": "application/pdf",
            "application/vnd.google-apps.map": "application/pdf",
            "application/vnd.google-apps.fusiontable": "application/pdf",
            "application/vnd.google-apps.jam": "application/pdf",
            "application/vnd.google-apps.photo": "image/jpeg",
            "application/vnd.google-apps.shortcut": None,  # shortcuts need target resolution
            "application/vnd.google-apps.audio": "audio/mpeg",
            "application/vnd.google-apps.video": "video/mp4",
        }
        
        request = None
        if mime_type in workspace_types:
            export_mime = workspace_types[mime_type]
            if export_mime is None:
                logger.warning(f"File {file_id} ({mime_type}) is a shortcut, skipping")
                return False
            logger.info(f"Exporting {file_name} ({mime_type}) as {export_mime}")
            request = service.files().export_media(fileId=file_id, mimeType=workspace_types[mime_type])
        else:
            # Try direct download for binary files (PDFs, images, etc.)
            try:
                request = service.files().get_media(fileId=file_id, supportsAllDrives=True)
            except Exception as e:
                logger.warning(f"Direct download failed for {file_id}, trying export as PDF: {e}")
                try:
                    request = service.files().export_media(fileId=file_id, mimeType="application/pdf")
                except Exception as e2:
                    logger.error(f"Export also failed for {file_id}: {e2}")
                    return False
        
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while done is False:
            status, done = downloader.next_chunk()
        
        with open(output_path, 'wb') as f:
            f.write(fh.getvalue())
        return True
    except Exception as e:
        logger.error(f"Failed to download/export file {file_id}: {e}")
        return False


def download_classroom_pdfs(output_dir: str = "classroom_pdfs") -> str:
    """Download all PDF attachments from recent Classroom assignments, OCR them, and save as text."""
    creds = get_google_credentials()
    if not creds:
        return "Google API credentials not configured."

    os.makedirs(output_dir, exist_ok=True)
    downloaded = []
    skipped = 0
    failed_downloads = []

    try:
        service = build('classroom', 'v1', credentials=creds)
        results = service.courses().list(courseStates=['ACTIVE']).execute()
        courses = results.get('courses', [])

        if not courses:
            return "No active Google Classroom courses found."

        import datetime
        cutoff = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=30)

        for course in courses:
            try:
                coursework = service.courses().courseWork().list(
                    courseId=course['id'],
                    courseWorkStates=['PUBLISHED'],
                    orderBy='updateTime desc',
                    pageSize=20
                ).execute()
                works = coursework.get('courseWork', [])

                for work in works:
                    # Skip old assignments
                    update_time = work.get('updateTime', '')
                    if update_time:
                        try:
                            updated = datetime.datetime.fromisoformat(update_time.replace('Z', '+00:00'))
                            if updated < cutoff:  # aware vs aware
                                skipped += 1
                                continue
                        except Exception:
                            pass

                    title = work.get('title', 'Untitled')
                    materials = work.get('materials', [])

                    for mat in materials:
                        if 'driveFile' in mat and 'driveFile' in mat['driveFile']:
                            df = mat['driveFile']['driveFile']
                            file_title = df.get('title', 'untitled')
                            file_id = df.get('id')
                            mime_type = df.get('mimeType', '')

                            if not file_id:
                                continue

                            # Check if we can download/export this file
                            try:
                                drive_service = build('drive', 'v3', credentials=creds)
                                file_meta = drive_service.files().get(
                                    fileId=file_id, 
                                    fields="mimeType,name,capabilities/canDownload", 
                                    supportsAllDrives=True
                                ).execute()
                                mime_type = file_meta.get('mimeType', '')
                                can_download = file_meta.get('capabilities', {}).get('canDownload', False)
                            except Exception as e:
                                logger.warning(f"Could not check file metadata for {file_title}: {e}")
                                skipped += 1
                                continue

                            # Skip if already downloaded
                            safe_name = "".join(c for c in file_title if c.isalnum() or c in (' ', '-', '_')).rstrip()
                            if not safe_name.lower().endswith('.pdf'):
                                safe_name += '.pdf'
                            # Sanitize course name for filesystem
                            safe_course_name = "".join(c for c in course['name'] if c.isalnum() or c in (' ', '-', '_', '@')).rstrip()
                            pdf_path = os.path.join(output_dir, f"{safe_course_name}_{safe_name}")
                            txt_path = pdf_path.replace('.pdf', '.txt')
                            
                            # Ensure output directory exists
                            os.makedirs(output_dir, exist_ok=True)
                            
                            if os.path.exists(pdf_path):
                                skipped += 1
                                continue

# Determine how to handle this file based on mime type
                            is_workspace = mime_type.startswith('application/vnd.google-apps.')
                            is_pdf = mime_type == 'application/pdf'

                            downloaded_this = False

                            if is_workspace:
                                # Google Workspace files (Docs, Sheets, Slides) - always export as PDF
                                logger.info(f"Exporting {file_title} ({mime_type}) as PDF")
                                if download_drive_file(file_id, pdf_path):
                                    try:
                                        import subprocess as _sp
                                        _sp.run(['pdftotext', '-layout', pdf_path, txt_path], check=True, timeout=60)
                                        downloaded.append(f"  {course['name']}/{file_title} (Google Doc → PDF + OCR)")
                                    except Exception as e:
                                        logger.warning(f"OCR failed for {file_title}: {e}")
                                        downloaded.append(f"  {course['name']}/{file_title} (Google Doc → PDF, OCR failed)")
                                    downloaded_this = True
                            elif mime_type == 'application/pdf':
                                # PDF file - check if downloadable
                                if can_download:
                                    if download_drive_file(file_id, pdf_path):
                                        try:
                                            import subprocess as _sp
                                            _sp.run(['pdftotext', '-layout', pdf_path, txt_path], check=True, timeout=60)
                                            downloaded.append(f"  {course['name']}/{file_title} (PDF + OCR)")
                                        except Exception as e:
                                            logger.warning(f"OCR failed for {file_title}: {e}")
                                            downloaded.append(f"  {course['name']}/{file_title} (PDF only, OCR failed)")
                                        downloaded_this = True
                                else:
                                    skipped += 1
                                    logger.info(f"Skipping {file_title} - cannot download (view-only)")
                            else:
                                # Other file types - try to download if allowed
                                if can_download:
                                    if download_drive_file(file_id, pdf_path):
                                        downloaded.append(f"  {course['name']}/{file_title}")
                                        downloaded_this = True
                                else:
                                    skipped += 1
                                    logger.info(f"Skipping {file_title} - cannot download (view-only)")

                            if not downloaded_this:
                                failed_downloads.append(f"{course['name']}/{file_title}")

            except Exception as e:
                logger.warning(f"Error downloading from {course['name']}: {e}")

    except Exception as e:
        return f"Error: {e}"

    result_parts = []
    if downloaded:
        result_parts.append(f"Downloaded {len(downloaded)} Classroom PDFs to {output_dir}/:")
        result_parts.extend(downloaded)
    if skipped:
        result_parts.append(f"\nSkipped {skipped} files (already downloaded or view-only)")
    if failed_downloads:
        result_parts.append(f"\nFailed to download {len(failed_downloads)} files (permission issues):")
        result_parts.extend(failed_downloads[:20])  # Limit output

    if not downloaded and not failed_downloads:
        return f"No new PDFs downloaded (skipped {skipped} already downloaded or view-only)."

    return "\n".join(result_parts)

    return f"Downloaded {len(downloaded)} Classroom PDFs to {output_dir}/:\n" + "\n".join(downloaded)


if __name__ == "__main__":
    print("Testing Gmail API...")
    print(get_unread_emails())
    print("\nTesting Google Classroom Assignments...")
    print(get_classroom_assignments())
    print("\nTesting Google Classroom Announcements...")
    print(get_classroom_announcements())
