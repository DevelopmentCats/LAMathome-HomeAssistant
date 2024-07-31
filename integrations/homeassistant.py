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
        if state['entity_id'].split('.')[0] in ('automation', 'light', 'switch', 'scene', 'script')
    }
    
    # Determine the action (turn_on, turn_off, or trigger)
    action = determine_action(user_input)
    
    # Remove action words and common words from user input for better matching
    clean_input = user_input.lower()
    for word in ["turn", "on", "off", "the", "activate", "deactivate", "trigger", "switch", "set"]:
        clean_input = clean_input.replace(word, "").strip()
    
    # Split the clean input into words and find the best match for each combination
    input_words = clean_input.split()
    best_match = None
    best_similarity = 0
    
    for i in range(len(input_words)):
        for j in range(i + 1, len(input_words) + 1):
            phrase = " ".join(input_words[i:j])
            match, similarity = find_best_match(phrase, entities.keys())
            if similarity > best_similarity:
                best_match = match
                best_similarity = similarity
    
    if best_match and best_similarity > 0.6:
        entity_id = entities[best_match]
        domain, _ = entity_id.split('.', 1)
        
        # Call the service
        url = f"{HA_URL}/api/services/{domain}/{action}"
        payload = {"entity_id": entity_id}
        
        try:
            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()
            action_map = {'turn_on': 'Turned on', 'turn_off': 'Turned off', 'trigger': 'Triggered'}
            return f"{action_map[action]} {best_match}"
        except requests.exceptions.RequestException as e:
            logging.error(f"Failed to control {best_match}: {e}")
            return f"Failed to control {best_match}: {e}"
    else:
        return f"I couldn't find a close match for '{clean_input}'. Available entities: {', '.join(entities.keys())}"
