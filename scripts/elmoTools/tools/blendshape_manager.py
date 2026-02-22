import json
import maya.cmds as cmds
import maya.api.OpenMaya as om

class BlendShapeManager:
    """
    Ultimate BlendShape I/O
    - Supports Live Targets (Connected Geometry)
    - Supports Baked Targets (Internal Data)
    - Supports Sparse Storage
    - Includes 'Reconstruct' tool to spawn physical meshes
    """

    def __init__(self):
        self.tolerance = 0.0001

    # --------------------------------------------------------------------------
    # API HELPER
    # --------------------------------------------------------------------------
    def get_api_node(self, node_name):
        sel = om.MSelectionList()
        try:
            sel.add(node_name)
            obj = sel.getDependNode(0)
            return om.MFnDependencyNode(obj)
        except:
            return None

    def get_points(self, node_name):
        """Returns list of [x,y,z] for a mesh."""
        sel = om.MSelectionList()
        try:
            sel.add(node_name)
            dag = sel.getDagPath(0)
            fn_mesh = om.MFnMesh(dag)
            points = fn_mesh.getPoints(om.MSpace.kObject)
            return points
        except:
            return None

    # --------------------------------------------------------------------------
    # EXPORT (Fixed for Live Targets)
    # --------------------------------------------------------------------------
    def extract_deltas(self, fn_node, base_name, base_idx, target_idx, item_idx):
        """
        Smart extraction: Checks for Live Geometry first, then Internal Data.
        """
        # 1. Check for Live Connection (inputGeomTarget)
        try:
            plug_input = fn_node.findPlug("inputTarget", False).elementByLogicalIndex(base_idx)
            plug_group = plug_input.child(0).elementByLogicalIndex(target_idx)
            plug_item = plug_group.child(0).elementByLogicalIndex(item_idx)
            
            plug_geom = plug_item.child(0) # inputGeomTarget
            
            # If connected, calculate diff from Base Mesh
            if plug_geom.isConnected:
                src_plug = plug_geom.source()
                src_node = src_plug.node()
                if src_node.hasFn(om.MFn.kMesh):
                    # It's a live mesh!
                    fn_src = om.MFnDependencyNode(src_node)
                    src_name = fn_src.name()
                    
                    # Calculate Live Deltas
                    base_pts = self.get_points(base_name)
                    tgt_pts = self.get_points(src_name)
                    
                    if not base_pts or not tgt_pts: return {}
                    
                    deltas = {}
                    # We assume topology matches for live targets
                    limit = min(len(base_pts), len(tgt_pts))
                    
                    for i in range(limit):
                        b = base_pts[i]
                        t = tgt_pts[i]
                        dx, dy, dz = t.x - b.x, t.y - b.y, t.z - b.z
                        
                        if (abs(dx) > self.tolerance or 
                            abs(dy) > self.tolerance or 
                            abs(dz) > self.tolerance):
                            deltas[str(i)] = [round(dx, 5), round(dy, 5), round(dz, 5)]
                    
                    return deltas

            # 2. Fallback to Baked Internal Data (inputPointsTarget)
            plug_points = plug_item.child(2) 
            data_obj = plug_points.asMObject()
            
            if data_obj.isNull():
                return {} # Empty target

            fn_points = om.MFnPointArrayData(data_obj)
            point_array = fn_points.array()

            plug_comp = plug_item.child(1) 
            comp_obj = plug_comp.asMObject()
            
            indices = []
            if not comp_obj.isNull():
                fn_comp = om.MFnSingleIndexedComponent(comp_obj)
                indices = fn_comp.getElements()
            else:
                indices = range(len(point_array))

            deltas = {}
            for i, vtx_idx in enumerate(indices):
                pt = point_array[i]
                if (abs(pt.x) > self.tolerance or 
                    abs(pt.y) > self.tolerance or 
                    abs(pt.z) > self.tolerance):
                    deltas[str(vtx_idx)] = [round(pt.x, 5), round(pt.y, 5), round(pt.z, 5)]

            return deltas

        except Exception as e:
            # print(f"Debug: Extraction failed {e}")
            return {}

    def export_blendshapes(self, nodes=None, file_path=None):
        if not nodes:
            nodes = cmds.ls(sl=True, type="blendShape")
            if not nodes:
                # History lookup
                sel = cmds.ls(sl=True) or []
                nodes = []
                for s in sel:
                    h = cmds.listHistory(s, type="blendShape") or []
                    nodes.extend(h)
                nodes = list(set(nodes))

        if not nodes:
            om.MGlobal.displayError("No BlendShapes found.")
            return

        data = {}

        for bs in nodes:
            if cmds.nodeType(bs) != "blendShape": continue

            fn_node = self.get_api_node(bs)
            
            # Base Geometry
            geom_hist = cmds.blendShape(bs, q=True, geometry=True)
            if not geom_hist: continue
            base_name = geom_hist[0]
            
            # Setup Data
            bs_data = {
                "baseGeometry": base_name,
                "vertexCount": cmds.polyEvaluate(base_name, v=True),
                "targets": {}
            }

            # Get Targets
            weight_indices = cmds.getAttr(bs + ".weight", multiIndices=True) or []

            for idx in weight_indices:
                alias = cmds.aliasAttr(f"{bs}.weight[{idx}]", q=True)
                w_val = cmds.getAttr(f"{bs}.weight[{idx}]")

                target_data = {
                    "index": idx,
                    "weight": w_val,
                    "items": {} 
                }

                # Find In-Betweens
                try:
                    plug_input = fn_node.findPlug("inputTarget", False).elementByLogicalIndex(0)
                    plug_group = plug_input.child(0).elementByLogicalIndex(idx)
                    plug_item_array = plug_group.child(0)

                    for i in range(plug_item_array.numElements()):
                        item_plug = plug_item_array.elementByPhysicalIndex(i)
                        logical_idx = item_plug.logicalIndex() # 6000
                        
                        # PASS BASE NAME TO HANDLE LIVE TARGETS
                        deltas = self.extract_deltas(fn_node, base_name, 0, idx, logical_idx)

                        if deltas:
                            target_data["items"][str(logical_idx)] = deltas
                except:
                    pass
                
                bs_data["targets"][alias] = target_data
            
            data[bs] = bs_data

        if file_path:
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=4)
            om.MGlobal.displayInfo(f"Exported to: {file_path}")
        
        return data

    # --------------------------------------------------------------------------
    # IMPORT (Standard Rig Restore)
    # --------------------------------------------------------------------------
    def import_blendshapes(self, file_path, target_geo=None):
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
        except:
            return

        for bs_name, bs_data in data.items():
            geo_name = target_geo if target_geo else bs_data["baseGeometry"]
            
            if not cmds.objExists(geo_name):
                om.MGlobal.displayError(f"Target '{geo_name}' missing.")
                continue

            # Create Node
            final_bs = bs_name
            if not cmds.objExists(bs_name):
                final_bs = cmds.blendShape(geo_name, n=bs_name)[0]
            
            fn_node = self.get_api_node(final_bs)

            for alias, target_info in bs_data["targets"].items():
                
                # Setup Plug
                idx = target_info["index"]
                
                # Collision check
                used = cmds.getAttr(final_bs + ".weight", multiIndices=True) or []
                if idx in used and alias not in cmds.aliasAttr(final_bs, q=True):
                    idx = max(used) + 1 if used else 0
                
                plug_str = f"{final_bs}.w[{idx}]"
                if not cmds.objExists(plug_str):
                    cmds.aliasAttr(alias, plug_str)
                    cmds.setAttr(plug_str, 0)
                
                # Apply Deltas
                for item_str, deltas in target_info["items"].items():
                    self._inject_deltas(fn_node, 0, idx, int(item_str), deltas)
                
                # Restore Weight
                cmds.setAttr(plug_str, target_info["weight"])

            om.MGlobal.displayInfo(f"Imported Data to {final_bs}")

    def _inject_deltas(self, fn_node, base_idx, target_idx, item_idx, deltas):
        points = om.MPointArray()
        indices = om.MIntArray()
        for v, pos in deltas.items():
            indices.append(int(v))
            points.append(om.MPoint(pos[0], pos[1], pos[2]))

        fn_comp = om.MFnSingleIndexedComponent()
        comp_obj = fn_comp.create(om.MFn.kMeshVertComponent)
        fn_comp.addElements(indices)
        
        fn_pdata = om.MFnPointArrayData()
        obj_pdata = fn_pdata.create(points)

        plug_input = fn_node.findPlug("inputTarget", False).elementByLogicalIndex(base_idx)
        plug_group = plug_input.child(0).elementByLogicalIndex(target_idx)
        plug_item = plug_group.child(0).elementByLogicalIndex(item_idx)
        
        plug_item.child(2).setMObject(obj_pdata) # Points
        plug_item.child(1).setMObject(comp_obj)  # Components

    # --------------------------------------------------------------------------
    # RECONSTRUCT (User Feature: Create Physical Meshes)
    # --------------------------------------------------------------------------
    def reconstruct_targets(self, file_path, base_geo=None):
        """
        Reads the JSON and spawns actual mesh objects for every target.
        """
        with open(file_path, 'r') as f:
            data = json.load(f)
            
        spawned_grp = cmds.group(em=True, n="Reconstructed_Targets_GRP")

        for bs_name, bs_data in data.items():
            base = base_geo if base_geo else bs_data["baseGeometry"]
            
            if not cmds.objExists(base):
                print(f"Base {base} missing, cannot reconstruct.")
                continue
                
            for alias, t_data in bs_data["targets"].items():
                # We usually only care about the 1.0 weight (6000)
                # But let's look for the highest weight item
                for item_idx, item_data in t_data["items"].items():
                    
                    # Duplicate Base
                    new_mesh = cmds.duplicate(base, n=f"{alias}_GEO")[0]
                    cmds.parent(new_mesh, spawned_grp)
                    
                    # Apply Deltas to Mesh Vertices
                    deltas = item_data
                    
                    # Move vertices
                    for vtx_id, offset in deltas.items():
                        cmds.move(offset[0], offset[1], offset[2], 
                                  f"{new_mesh}.vtx[{vtx_id}]", 
                                  r=True) # Relative move
                    
                    print(f"Reconstructed: {new_mesh}")

# Usage:
io = BlendShapeManager()
io.export_blendshapes(file_path="C:/tmp/face_data.json")

# Option A: Restore Rig (Invisible)
# io.import_blendshapes("C:/tmp/face_data.json")

# Option B: I want to see the meshes!
# io.reconstruct_targets("C:/temp/face_data.json")