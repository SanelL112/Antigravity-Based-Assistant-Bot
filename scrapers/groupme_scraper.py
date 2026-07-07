import os
import logging
import requests
from dotenv import load_dotenv

logger = logging.getLogger(__name__)
load_dotenv()

GROUPME_ACCESS_TOKEN = os.getenv("GROUPME_ACCESS_TOKEN")

def get_groups():
    """Fetch all groups the user is a part of to find their IDs."""
    if not GROUPME_ACCESS_TOKEN:
        return "GroupMe API token not configured."

    url = "https://api.groupme.com/v3/groups"
    params = {"token": GROUPME_ACCESS_TOKEN, "per_page": 100}
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        groups = response.json().get('response', [])
        
        if not groups:
            return "No groups found."
            
        result = ["📋 **Your GroupMe Groups:**"]
        for g in groups:
            result.append(f"- {g['name']} (ID: {g['id']})")
        return "\n".join(result)
    except Exception as e:
        logger.error(f"Error fetching groups: {e}")
        return f"Error connecting to GroupMe: {e}"

def get_latest_messages(group_id, limit=5):
    """Fetch the latest messages from a specific GroupMe group."""
    if not GROUPME_ACCESS_TOKEN or GROUPME_ACCESS_TOKEN == "your_groupme_token":
        return "GroupMe API token not configured. Please add GROUPME_ACCESS_TOKEN to .env."

    url = f"https://api.groupme.com/v3/groups/{group_id}/messages"
    params = {
        "token": GROUPME_ACCESS_TOKEN,
        "limit": limit
    }

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        messages = response.json().get('response', {}).get('messages', [])
        
        if not messages:
            return "No messages found in this group."
            
        result = [f"💬 **Recent GroupMe Messages:**"]
        for msg in reversed(messages):
            sender = msg.get('name', 'Unknown')
            text = msg.get('text', '')
            if text:
                result.append(f"**{sender}**: {text}")
                
        return "\n".join(result)

    except Exception as e:
        logger.error(f"Error fetching GroupMe messages: {e}")
        return f"Error connecting to GroupMe: {e}"

if __name__ == "__main__":
    print("Testing GroupMe API connection...")
    print(get_groups())
