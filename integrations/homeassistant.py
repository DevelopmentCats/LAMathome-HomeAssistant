import requests
import logging
from difflib import SequenceMatcher
from utils.get_env import HA_URL, HA_TOKEN

def similar(a, b):
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()

def find_best_match(user_input, entities):
    best_match = max(entities, key=lambda x: similar(user_input, x))
    similarity = similar(user_input, best_match)
    return best_match, similarity

def determine_action(user_input):
    if "turn on" in user_input.lower() or "activate" in user_input.lower():
        return "turn_on"
    elif "turn off" in user_input.lower() or "deactivate" in user_input.lower():
        return "turn_off"
    else:
        return "trigger"

def homeassistant(user_input):
    """Controls Home Assistant entities based on user input."""
    
    headers = {
        "Authorization": f"Bearer {HA_TOKEN}",
        "Content-Type": "application/json"
    }
    
    # Get the list of entities
    response = requests.get(f"{HA_URL}/api/states", headers=headers)
    if response.status_code != 200:
        return f"Failed to retrieve states: {response.status_code}"
    states = response.json()
    
    # Extract entity names and IDs
    entities = {
        state['attributes'].get('friendly_name', ''): state['entity_id']
        for state in states
        if state['entity_id'].split('.')[0] in ('automation', 'light', 'switch')
    }
    
    # Determine the action (turn_on, turn_off, or trigger)
    action = determine_action(user_input)
    
    # Remove action words from user input for better matching
    clean_input = user_input.lower().replace("turn on", "").replace("turn off", "").replace("activate", "").replace("deactivate", "").strip()
    
    # Find the best match
    best_match, similarity = find_best_match(clean_input, entities.keys())
    
    # Set a threshold for similarity (e.g., 0.7 for 70% similarity)
    if similarity < 0.7:
        return f"I couldn't find a close match for '{clean_input}'. Did you mean '{best_match}'?"

    entity_id = entities[best_match]
    entity_type, _ = entity_id.split('.', 1)
    
    # Determine the appropriate service based on the entity type and action
    service = f"{entity_type}/{action}" if entity_type == 'automation' else f"homeassistant/{action}"
    
    # Trigger the action
    url = f"{HA_URL}/api/services/{service}"
    payload = {"entity_id": entity_id}
    
    response = requests.post(url, json=payload, headers=headers)
    if response.status_code == 200:
        action_map = {'turn_on': 'Turned on', 'turn_off': 'Turned off', 'trigger': 'Triggered'}
        return f"{action_map[action]} {best_match}"
    else:
        return f"Failed to control {best_match}: {response.status_code}"
