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


class VesselGraph:

    def __init__(self, vessel):
        self.vessel = vessel
        self.parts = vessel.parts.all
        self.node_index = {}
        self.nodes = []
        self.edges = []
        self.node_rows = []
        self.edge_rows = []
        self.node_features = None
        self.edge_index = None
        self.edge_features = None
        self.graph = None
        
    def build_node_index(self):
        self.node_index = {part: part_idx for part_idx, part in enumerate(self.vessel.parts.all)}
        
    def build_nodes_edges_edge_rows(self):
        for part_idx, part in enumerate(self.vessel.parts.all):
            parent_name = part.parent.name if part.parent else None
            child_names = [child.name for child in part.children] if part.children else None
            # HardCoded Nodes
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
            # Append Node to all Nodes
            self.nodes.append(node)   
                
            # Edges - Adding parent & child edges allows information to flow both ways
            if part.parent is not None:
                parent_idx = self.node_index[part.parent]
                child_idx = self.node_index[part]
                # Append to Edges Tensor
                self.edges.append([parent_idx, child_idx])
                self.edges.append([child_idx, parent_idx])
            # Edge Features
            features = [float(part.axially_attached), float(part.radially_attached)]
            # Append feature twice for parent <-> child connection
            self.edge_rows.append(features)
            self.edge_rows.append(features)

    def build_node_rows(self):
        for node in self.nodes:
            row = []
            # Add Static & Dynamic Node attributes
            for feature_name in NODE_STATIC_FEATURES + NODE_DYNAMIC_FEATURES:
                row.append(node[feature_name])
            row.append(node["resource_count"])
            self.node_rows.append(row)
            
    def build_node_features(self):
        # Node Feature Tensor
        self.node_features = torch.tensor(self.node_rows, dtype=torch.float32)
        
    def build_edge_features(self):
        # Edge Index
        self.edge_index = torch.tensor(self.edges, dtype=torch.long).T.contiguous()
        # Edge Features
        self.edge_features = torch.tensor(self.edge_rows, dtype=torch.float32)
    
    def build_graph(self):
        self.graph = Data(
            x=self.node_features,
            edge_index=self.edge_index,
            edge_attr=self.edge_features
        )

    def build_graph_from_init(self):
        self.build_node_index()
        self.build_nodes_edges_edge_rows()
        self.build_node_rows()
        self.build_node_features()
        self.build_edge_features()
        self.build_graph()
        
    def update_nodes(self):
        # Update dynamic node attributes
        for part, part_idx in self.node_index.items():
            for feature_name in NODE_STATIC_FEATURES + NODE_DYNAMIC_FEATURES:
                self.nodes[part_idx][feature_name] = getattr(part, feature_name)
    
    def update_node_rows(self):
        # Update dynamic node row attributes
        for node_idx, node in enumerate(self.nodes):
            row = []
            for feature_name in NODE_STATIC_FEATURES + NODE_DYNAMIC_FEATURES:
                row.append(node[feature_name])
            row.append(node["resource_count"])
            self.node_rows[node_idx] = row
    
    def update_graph(self):
        self.graph.x = self.node_features
        self.graph.edge_attr = self.edge_features
    
    def update_graph_from_live(self):
        self.update_nodes()
        self.update_node_rows()
        self.build_node_features()
        self.build_edge_features()
        self.update_graph()
        
    




def main():
    
    conn = krpc.connect(name="Build Craft Vessel Live\n")
    vessel = conn.space_center.active_vessel

    vesselGraph = VesselGraph(vessel=vessel)
    vesselGraph.build_graph_from_init()
    
    try:
        while True:
            start_time = time.perf_counter()
            
            # Time to Update graph
            update_start_time = time.perf_counter()
            vesselGraph.update_graph_from_live()
            update_elapsed_time = time.perf_counter() - update_start_time
            
            # Sum the mass column in the PyTorch Geometric feature tensor
            feature_names = (NODE_STATIC_FEATURES + NODE_DYNAMIC_FEATURES + ["resource_count"])
            mass_column = feature_names.index("mass")
            total_mass = vesselGraph.graph.x[:, mass_column].sum().item()
            print(f"Nodes: {len(vesselGraph.nodes)}, update t: {update_elapsed_time:.4f}s, Mass from graph.x: {total_mass:.2f}kg\n")
            
            elapsed_time = time.perf_counter() - start_time
            time.sleep(max(2.0 - elapsed_time, 0.0))

    except KeyboardInterrupt:
        print("[Main] Ctrl+C received. Stopping Graph Generation")
        



if __name__ == "__main__":
    main()
    