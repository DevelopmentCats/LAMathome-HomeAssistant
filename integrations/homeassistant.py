import requests
import logging
from utils.get_env import HA_TOKEN, HA_URL
from webcolors import name_to_rgb

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
            friendly_name = state['attributes'].get('friendly_name', entity_id).lower()
            entities[friendly_name] = {
                'entity_id': entity_id,
                'state': state['state'],
                'attributes': state['attributes']
            }
        return entities
    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to fetch entities: {e}")
        return {}

def call_service(domain, service, data):
    """Call a Home Assistant service."""
    headers = {
        "Authorization": f"Bearer {HA_TOKEN}",
        "Content-Type": "application/json"
    }
    url = f"{HA_URL}/api/services/{domain}/{service}"
    
    try:
        response = requests.post(url, json=data, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to call service: {e}")
        raise

def control_homeassistant(parsed_input):
    """Controls Home Assistant entities, scenes, and triggers based on LLM parsed input."""
    entities = get_entities()
    
    parts = parsed_input.split()
    if len(parts) < 3 or parts[0].lower() != "homeassistant":
        return "Invalid command format. Expected: HomeAssistant [Entity/Scene/Trigger] [Action]"
    
    target_name = " ".join(parts[1:-1]).lower()
    action = parts[-1].lower()
    
    # Check if it's a scene
    if target_name.startswith("scene "):
        scene_name = target_name[6:]
        if scene_name in entities:
            try:
                call_service("scene", "turn_on", {"entity_id": entities[scene_name]['entity_id']})
                return f"Successfully activated scene: {scene_name}"
            except Exception as e:
                logging.error(f"Failed to activate scene {scene_name}: {e}")
                return f"Failed to activate scene {scene_name}: {str(e)}"
        else:
            return f"Couldn't find the scene: {scene_name}"
    
    # Check if it's a trigger (automation)
    elif target_name.startswith("trigger ") or target_name.startswith("automation "):
        automation_name = target_name.split(" ", 1)[1]
        if automation_name in entities:
            try:
                call_service("automation", "trigger", {"entity_id": entities[automation_name]['entity_id']})
                return f"Successfully triggered automation: {automation_name}"
            except Exception as e:
                logging.error(f"Failed to trigger automation {automation_name}: {e}")
                return f"Failed to trigger automation {automation_name}: {str(e)}"
        else:
            return f"Couldn't find the automation: {automation_name}"
    
    # If not a scene or trigger, proceed with entity control
    if target_name in entities:
        entity = entities[target_name]
        entity_id = entity['entity_id']
        domain = entity_id.split('.')[0]
        
        try:
            if action in ["on", "off", "toggle"]:
                service = "turn_on" if action == "on" else "turn_off" if action == "off" else "toggle"
                call_service(domain, service, {"entity_id": entity_id})
                return f"Successfully {service.replace('_', ' ')} {target_name}"
            
            elif action.startswith("rgb("):
                rgb_values = [int(val) for val in action[4:-1].split(',')]
                if len(rgb_values) != 3 or not all(0 <= val <= 255 for val in rgb_values):
                    return "Invalid RGB values. Use format: rgb(r,g,b) with values between 0 and 255."
                call_service(domain, "turn_on", {"entity_id": entity_id, "rgb_color": rgb_values})
                return f"Successfully set {target_name} color to {action}"
            
            elif action.endswith('%'):
                value = float(action[:-1])
                if 0 <= value <= 100:
                    call_service(domain, "turn_on", {"entity_id": entity_id, "brightness_pct": value})
                    return f"Successfully set {target_name} brightness to {action}"
                else:
                    return "Invalid brightness percentage. Use a value between 0 and 100."
            
            elif action.startswith("set "):
                # Handle various "set" commands
                set_parts = action.split()
                if len(set_parts) < 3:
                    return "Invalid set command. Use format: set [attribute] [value]"
                attribute = set_parts[1]
                value = " ".join(set_parts[2:])
                
                try:
                    # Try to convert value to number if possible
                    value = float(value) if '.' in value else int(value)
                except ValueError:
                    pass  # Keep value as string if it's not a number
                
                call_service(domain, "set_" + attribute, {"entity_id": entity_id, attribute: value})
                return f"Successfully set {target_name} {attribute} to {value}"
            
            else:
                # Try to interpret action as a color name
                try:
                    rgb = name_to_rgb(action)
                    call_service(domain, "turn_on", {"entity_id": entity_id, "rgb_color": [rgb.red, rgb.green, rgb.blue]})
                    return f"Successfully set {target_name} color to {action}"
                except ValueError:
                    return f"Invalid action: {action}. Use 'on', 'off', 'toggle', 'rgb(r,g,b)', a valid color name, a percentage (e.g., '50%') for brightness, or 'set [attribute] [value]'."
        
        except Exception as e:
            logging.error(f"Failed to control {target_name}: {e}")
            return f"Failed to control {target_name}: {str(e)}"
    else:
        return f"Couldn't find the entity: {target_name}"

def get_entity_state(entity_name):
    """Get the state of a Home Assistant entity."""
    entities = get_entities()
    if entity_name.lower() in entities:
        entity = entities[entity_name.lower()]
        return {
            "entity_id": entity['entity_id'],
            "state": entity['state'],
            "attributes": entity['attributes']
        }
    else:
        return {"error": f"Couldn't find a matching entity for {entity_name}"}

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        print(control_homeassistant(" ".join(sys.argv[1:])))
