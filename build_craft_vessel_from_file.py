import os
import sys
import glob

import re
from pathlib import Path

import matplotlib.pyplot as plt

import json

# from craft_graph import parse_craft, build_graph

file_name = "P-37 Duchess.craft"


def parse_craft(path):
    """
    Parse the KSP craft file and find the number of parts
    """
    parts = []
    current = None
    depth = 0          # brace nesting depth
    pending_block = None

    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for raw in f:
            line = raw.strip()
            if not line:
                continue

            if line == "{":
                depth += 1
                if pending_block == "PART" and depth == 1:
                    current = {"id": None, "links": [], "parent": None}
                pending_block = None
                continue
            
            
            # key, _, value = (s.strip() for s in line.partition(" = "))
            # # print(value,"\n")
            # if key == "name":
            #     # print(key, " ", value,"\n")
                
            #     if "Module" not in value:
            #         print(key, " ", value,"\n") 
                


            if line == "}":
                depth -= 1
                if depth == 0 and current is not None:
                    parts.append(current)
                    current = None
                continue
            
            

            # Anything else is a block header (PART, MODULE, EVENTS, ...)
            pending_block = line if depth == 0 else None

    return parts



def build_module_catalogue(game_data_path):

    module_names = set()

    for file in Path(game_data_path).rglob("*.cfg"):

        content = file.read_text(
            encoding="utf-8",
            errors="ignore"
        )

        modules = re.findall(
            r"MODULE\s*\{\s*name\s*=\s*(\w+)",
            content
        )

        module_names.update(modules)

    return sorted(module_names)



def main():
    # parts = parse_craft(file_name)
    
    # game_data_path = r"C:\Program Files (x86)\Steam\steamapps\common\Kerbal Space Program\GameData"
    
    # module_catalogue = build_module_catalogue(game_data_path)

    # print(module_catalogue)
    # print(len(module_catalogue))
    
    
    CLASS_PART_LIST = {
        "antenna": ["deployable", "deployed", "can_transmit"],
        "cargo_bay": ["open"],
        "control_surface": ["pitch_enabled", "yaw_enabled", "roll_enabled", "authority_limiter", "inverted", "deployed", "deflection_override", "deflection", "surface_area", "available_torque"],
        "decoupler": ["decoupled", "staged", "impulse", "is_omni_decoupler"],
        "docking_port": ["reengage_distance", "has_shield", "shielded", "can_rotate", "maximum_rotation", "minimum_rotation", "rotation_target", "rotation_locked", "position", "direction", "rotation"],
        "engine": ["active", "thrust", "available_thrust", "max_thrust", "max_vacuum_thrust", "thrust_limit", "specific_impulse", "vacuum_specific_impulse", "has_fuel", "flameout", "throttle", "throttle_locked", "independant_throttle", "can_restart", "can_shutdown", "has_modes", "auto_mode_switch", "gimballed", "gimbal_range", "gimbal_locked", "gimbal_limit", "gimbal_override", "gimbal_actuation", "available_torque", "can_reverse_thrust", "thrust_reversed"],
        "reaction_wheel": ["active", "broken", "available_torque", "max_torque", "authority_limiter"],
        "intake": ["open", "speed", "flow", "area"],
        "leg": ["deployable", "deployed", "is_grounded"],
        "rcs": ["active", "enabled", "pitch_enabled", "yaw_enabled", "roll_enabled", "forward_enabled", "up_enabled", "right_enabled", "input_override", "rotation_override", "translation_override", "available_torque", "available_force", "available_thrust", "max_thrust", "max_vacuum_thrust", "thrust_limit", "specific_impulse", "vacuum_specific_impulse", "has_fuel"],
        "wheel": ["radius", "grounded", "has_brakes", "brakes", "auto_friction_control", "manual_friction_control", "deployable", "deployed", "powered", "motor_enabled", "motor_inverted", "motor_output", "traction_control_enabled", "traction_control", "drive_limiter", "steerable", "steering_enabled", "steering_inverted", "steering_angle_auto", "steering_angle_limit", "deflection"]
        }
    
    CLASS_ENGINE_LIST = {
        
    }
    

    # with open("module_catalogue.json", "w") as file:

    # json.dump(module_catalogue, file, indent=4)
    
    
    
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
    
 

    
    
    
    