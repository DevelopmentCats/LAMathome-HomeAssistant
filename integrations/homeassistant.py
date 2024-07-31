import requests
import logging
from utils.get_env import HA_URL, HA_TOKEN

def homeassistant(automation):
    """Runs the specified automation in Home Assistant using the API."""
    
    headers = {
        "Authorization": f"Bearer {HA_TOKEN}",
        "Content-Type": "application/json"
    }
    
    # Get the list of automations
    url = f"{HA_URL}/api/services/automation/trigger"
    
    # Find the automation entity ID
    response = requests.get(f"{HA_URL}/api/states", headers=headers)
    
    if response.status_code != 200:
        logging.error(f"Failed to retrieve states: {response.status_code}")
        return
    
    states = response.json()
    
    automation_entity_id = None
    for state in states:
        if state['entity_id'].startswith('automation.') and state['attributes'].get('friendly_name') == automation:
            automation_entity_id = state['entity_id']
            break
    
    if not automation_entity_id:
        logging.error(f"Automation '{automation}' not found")
        return
    
    logging.info(f"Found automation '{automation}' with entity ID: {automation_entity_id}")
    
    # Trigger the automation
    payload = {
        "entity_id": automation_entity_id
    }
    
    response = requests.post(url, json=payload, headers=headers)
    
    if response.status_code == 200:
        logging.info(f"Successfully triggered automation '{automation}'")
    else:
        logging.error(f"Failed to trigger automation '{automation}': {response.status_code}")

# Example usage
homeassistant("Your Automation Name")
