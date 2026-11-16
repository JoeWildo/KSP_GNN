import os
import sys
import glob
import time

import matplotlib.pyplot as plt
import torch
from torch_geometric.data import Data

import krpc
from krpc.error import RPCError

NODE_STATIC_FEATURES  = ["dry_mass", "max_temperature", "max_skin_temperature"]
NODE_DYNAMIC_FEATURES = ["mass", "dynamic_pressure", "temperature", "skin_temperature"]
NODE_ONE_HOT_FEATURES = ["resources"]


CLASS_PART_LIST = {
    "antenna": ["deployable", "deployed", "can_transmit"],
    "cargo_bay": ["open"],
    "control_surface": ["pitch_enabled", "yaw_enabled", "roll_enabled", "authority_limiter", "inverted", "deployed", "deflection_override", "deflection", "surface_area", "available_torque"],
    "decoupler": ["decoupled", "staged", "impulse", "is_omni_decoupler"],
    "docking_port": ["reengage_distance", "has_shield", "shielded", "can_rotate", "maximum_rotation", "minimum_rotation", "rotation_target", "rotation_locked", "position", "direction", "rotation"],
    "reaction_wheel": ["active", "broken", "available_torque", "max_torque", "authority_limiter"],
    "intake": ["open", "speed", "flow", "area"],
    "leg": ["deployable", "deployed", "is_grounded"],
    "rcs": ["active", "enabled", "pitch_enabled", "yaw_enabled", "roll_enabled", "forward_enabled", "up_enabled", "right_enabled", "input_override", "rotation_override", "translation_override", "available_torque", "available_force", "available_thrust", "max_thrust", "max_vacuum_thrust", "thrust_limit", "specific_impulse", "vacuum_specific_impulse", "has_fuel"],
    "wheel": ["radius", "grounded", "has_brakes", "brakes", "auto_friction_control", "manual_friction_control", "deployable", "deployed", "powered", "motor_enabled", "motor_inverted", "motor_output", "traction_control_enabled", "traction_control", "drive_limiter", "steerable", "steering_enabled", "steering_inverted", "steering_angle_auto", "steering_angle_limit", "deflection"]
    }

# CLASS_PART_LIST = {
#     "antenna": ["deployable", "deployed", "can_transmit"],
#     "cargo_bay": ["open"],
#     "control_surface": ["pitch_enabled", "yaw_enabled", "roll_enabled", "authority_limiter", "inverted", "deployed", "deflection_override", "deflection", "surface_area", "available_torque"],
#     "decoupler": ["decoupled", "staged", "impulse", "is_omni_decoupler"],
#     "docking_port": ["reengage_distance", "has_shield", "shielded", "can_rotate", "maximum_rotation", "minimum_rotation", "rotation_target", "rotation_locked", "position", "direction", "rotation"],
#     "engine": ["active", "thrust", "available_thrust", "max_thrust", "max_vacuum_thrust", "thrust_limit", "specific_impulse", "vacuum_specific_impulse", "has_fuel", "flameout", "throttle", "throttle_locked", "independant_throttle", "can_restart", "can_shutdown", "has_modes", "gimballed", "gimbal_range", "gimbal_locked", "gimbal_limit", "gimbal_override", "gimbal_actuation", "available_torque", "can_reverse_thrust", "thrust_reversed"],
#     "reaction_wheel": ["active", "broken", "available_torque", "max_torque", "authority_limiter"],
#     "intake": ["open", "speed", "flow", "area"],
#     "leg": ["deployable", "deployed", "is_grounded"],
#     "rcs": ["active", "enabled", "pitch_enabled", "yaw_enabled", "roll_enabled", "forward_enabled", "up_enabled", "right_enabled", "input_override", "rotation_override", "translation_override", "available_torque", "available_force", "available_thrust", "max_thrust", "max_vacuum_thrust", "thrust_limit", "specific_impulse", "vacuum_specific_impulse", "has_fuel"],
#     "wheel": ["radius", "grounded", "has_brakes", "brakes", "auto_friction_control", "manual_friction_control", "deployable", "deployed", "powered", "motor_enabled", "motor_inverted", "motor_output", "traction_control_enabled", "traction_control", "drive_limiter", "steerable", "steering_enabled", "steering_inverted", "steering_angle_auto", "steering_angle_limit", "deflection"]
#     }


def main():
    
    conn = krpc.connect(name="Build Craft Vessel Live\n")
    vessel = conn.space_center.active_vessel

    node_index = {}
    nodes = []
    edges = []
    node_rows = []
    edge_rows = []
    node_features = None
    edge_index = None
    edge_features = None
    graph = None
        
    node_index = {part: part_idx for part_idx, part in enumerate(vessel.parts.all)}
    
    # while True:
        
    for part_idx, part in enumerate(vessel.parts.all):
        parent_name = part.parent.name if part.parent else None
        child_names = [child.name for child in part.children] if part.children else None
        # HardCoded Node features
        node = {
            "id": part_idx,
            "name": part.name,
            "parent": parent_name,
            "children": child_names,
            "resource_count": len(part.resources.names),
            "resources": part.resources.names
        }
        # SoftCoded Node features
        for feature_name in NODE_STATIC_FEATURES + NODE_DYNAMIC_FEATURES:
            node[feature_name] = getattr(part, feature_name)
        # Part Class features
        for class_name, feature_names in CLASS_PART_LIST.items():
            component = getattr(part, class_name, None)
            for feature_name in feature_names:
                value = None
                if component is not None:
                    try:
                        value = getattr(component, feature_name, None)
                    except (RuntimeError, RPCError):
                        value = None            
                node[f"{class_name}_{feature_name}"] = (0 if value is None else value)
        # One-Hot Encoded Node features
        
        # Append Node to all Nodes
        nodes.append(node)
        
        # Edges - Adding parent & child edges allows information to flow both ways
        if part.parent is not None:
            parent_idx = node_index[part.parent]
            child_idx = node_index[part]
            # Append to Edges Tensor
            edges.append([parent_idx, child_idx])
            edges.append([child_idx, parent_idx])
        # Edge Features
        features = [float(part.axially_attached), float(part.radially_attached)]
        # Append feature twice for parent <-> child connection
        edge_rows.append(features)
        edge_rows.append(features)

    for node in nodes:
        row = []
        # Add Static & Dynamic Node attributes
        for feature_name in NODE_STATIC_FEATURES + NODE_DYNAMIC_FEATURES:
            row.append(node[feature_name])
        # Part Class features
        for class_name, feature_names in CLASS_PART_LIST.items():
            for feature_name in feature_names:
                value = node.get(f"{class_name}_{feature_name}", 0)
                row.append(value)
        row.append(node["resource_count"])
        node_rows.append(row)
    
    # Node Feature Tensor
    node_features = torch.tensor(node_rows, dtype=torch.float32)
    # Edge Index
    edge_index = torch.tensor(edges, dtype=torch.long).T.contiguous()
    # Edge Features
    edge_features = torch.tensor(edge_rows, dtype=torch.float32)
    
    graph = Data(
        x=node_features,
        edge_index=edge_index,
        edge_attr=edge_features
    )
    
    print(graph)
        
 



if __name__ == "__main__":
    main()
    