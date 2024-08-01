import requests
import logging
from difflib import get_close_matches
from utils.get_env import HA_TOKEN, HA_URL

def get_entities():
    """Fetch the list of entities and their states from Home Assistant API."""
    headers = {
        "Authorization": f"Bearer {HA_TOKEN}",
        "Content-Type": "application/json"
    }
    url = f"{HA_URL}/api/states"
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        states = response.json()
        entities = {}
        for state in states:
            entity_id = state['entity_id']
            friendly_name = state['attributes'].get('friendly_name', entity_id)
            current_state = state['state']
            entities[friendly_name.lower()] = {
                'entity_id': entity_id,
                'state': current_state
            }
        return entities
    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to fetch entities: {e}")
        return {}

def control_homeassistant(user_input):
    """Controls Home Assistant entities based on user input."""
    headers = {
        "Authorization": f"Bearer {HA_TOKEN}",
        "Content-Type": "application/json"
    }
    
    # Get the list of entities and their states
    entities = get_entities()
    
    # Parse the user input
    parts = user_input.split()
    if len(parts) < 3:
        return "Invalid command format. Please use: HomeAssistant [Entity] [Action]"
    
    entity_name = " ".join(parts[1:-1]).lower()
    action = parts[-1].lower()
    
    # Find the best match for the entity
    best_match = get_close_matches(entity_name, entities.keys(), n=1, cutoff=0.6)
    
    if best_match:
        entity = entities[best_match[0]]
        entity_id = entity['entity_id']
        current_state = entity['state']
        
        # Determine the action based on the current state and user input
        if action in ["on", "off"]:
            service = "turn_on" if action == "on" else "turn_off"
        elif action == "toggle":
            service = "toggle"
        else:
            try:
                value = float(action)
                service = "set_value"
            except ValueError:
                return f"Invalid action: {action}. Use 'on', 'off', 'toggle', or a numeric value."
        
        # Call the service
        domain = entity_id.split('.')[0]
        url = f"{HA_URL}/api/services/{domain}/{service}"
        payload = {"entity_id": entity_id}
        
        if service == "set_value":
            payload["value"] = value
        
        try:
            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()
            return f"Successfully {service.replace('_', ' ')} {best_match[0]}"
        except requests.exceptions.RequestException as e:
            logging.error(f"Failed to control {best_match[0]}: {e}")
            return f"Failed to control {best_match[0]}: {e}"
    else:
        return f"Couldn't find a matching entity. Available entities: {', '.join(entities.keys())}"

if __name__ == "__main__":
    # This allows you to test the function directly
    import sys
    if len(sys.argv) > 1:
        print(control_homeassistant(" ".join(sys.argv[1:])))
