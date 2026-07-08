import os
import json
import datetime
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def get_google_creds():
    token_path = os.path.join(BASE_DIR, "..", "token.json")
    if os.path.exists(token_path):
        with open(token_path, "r") as f:
            creds_data = json.load(f)
        return Credentials.from_authorized_user_info(creds_data)
    return None

def rescue():
    creds = get_google_creds()
    if not creds:
        print("No credentials available")
        return
    drive = build("drive", "v3", credentials=creds)
    classroom = build("classroom", "v1", credentials=creds)
    
    thirty_days_ago = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=30)).isoformat().replace("+00:00", "Z")
    
    output = "\n\n## Exhaustive Raw Document Index (Added by System)\n\n### Google Docs & Shared Files\n"
    
    # Docs
    query = f"mimeType='application/vnd.google-apps.document' and modifiedTime > '{thirty_days_ago}' and trashed=false"
    results = drive.files().list(q=query, fields="files(id, name)", supportsAllDrives=True, includeItemsFromAllDrives=True, corpora="allDrives").execute()
    for f in results.get("files", []):
        output += f"- {f['name']}\n"
        
    output += "\n### Google Classroom Assignments & PDFs\n"
    
    # Classroom
    courses = classroom.courses().list(courseStates=["ACTIVE"]).execute().get("courses", [])
    for c in courses:
        works = classroom.courses().courseWork().list(courseId=c["id"]).execute().get("courseWork", [])
        for w in works:
            output += f"- [{c['name']}] {w.get('title', 'Untitled')}\n"
            materials = w.get("materials", [])
            for m in materials:
                if "driveFile" in m and "driveFile" in m["driveFile"]:
                    output += f"  - Attachment: {m['driveFile']['driveFile'].get('title')}\n"
                    
    with open(os.path.join(BASE_DIR, "..", "mega_index.md"), "a") as f:
        f.write(output)
        
    with open(os.path.join(BASE_DIR, "..", "curated_brain.md"), "a") as f:
        f.write(output)

if __name__ == "__main__":
    rescue()
    print("Rescued documents to index.")
