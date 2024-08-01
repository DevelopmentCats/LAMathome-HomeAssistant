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
    user_input = user_input.lower()
    if "on" in user_input or "activate" in user_input:
        return "turn_on"
    elif "off" in user_input or "deactivate" in user_input:
        return "turn_off"
    else:
        return "set"

def control_homeassistant(user_input):
    """Controls Home Assistant entities based on user input."""
    
    headers = {
        "Authorization": f"Bearer {HA_TOKEN}",
        "Content-Type": "application/json"
    }
    
    # Get the list of entities
    try:
        response = requests.get(f"{HA_URL}/api/states", headers=headers)
        response.raise_for_status()
        states = response.json()
    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to retrieve states: {e}")
        return f"Failed to retrieve states: {e}"
    
    # Extract entity names and IDs
    entities = {
        state['attributes'].get('friendly_name', '').lower(): state['entity_id']
        for state in states
    }
    
    # Parse the user input
    parts = user_input.split()
    if len(parts) < 3:
        return "Invalid command format. Please use: HomeAssistant [Entity] [Action]"
    
    entity_name = " ".join(parts[1:-1]).lower()
    action = parts[-1].lower()
    
    # Determine the action
    ha_action = determine_action(action)
    
    # Find the best match for the entity
    best_match, similarity = find_best_match(entity_name, entities.keys())
    
    if similarity > 0.6:
        entity_id = entities[best_match]
        domain, _ = entity_id.split('.', 1)
        
        # Call the service
        url = f"{HA_URL}/api/services/{domain}/{ha_action}"
        payload = {"entity_id": entity_id}
        
        if ha_action == "set":
            try:
                value = float(action)
                payload["value"] = value
            except ValueError:
                return f"Invalid value for set action: {action}"
        
        try:
            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()
            action_map = {'turn_on': 'Turned on', 'turn_off': 'Turned off', 'set': 'Set'}
            return f"{action_map[ha_action]} {best_match}"
        except requests.exceptions.RequestException as e:
            logging.error(f"Failed to control {best_match}: {e}")
            return f"Failed to control {best_match}: {e}"
    else:
        return f"Couldn't find a close match for '{entity_name}'. Available entities: {', '.join(entities.keys())}"

if __name__ == "__main__":
    # This allows you to test the function directly
    import sys
    if len(sys.argv) > 1:
        print(control_homeassistant(" ".join(sys.argv[1:])))
