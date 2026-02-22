import maya.cmds as cmds
import maya.api.OpenMaya as om
import maya.api.OpenMayaAnim as oma
import json
import os


def save_geo(file_path):
    """
    Saves Topology/Geometry for MESHES. 

    Args:
        file_path (str): Full path to save the JSON file.
    """
    sel = om.MGlobal.getActiveSelectionList()
    if sel.length() == 0:
        om.MGlobal.displayError("Nothing selected.")
        return

    # Get DagPath
    dag_path = sel.getDagPath(0)

    # Ensure the Shape
    if dag_path.node().hasFn(om.MFn.kTransform):
        dag_path.extendToShape()

    # MESH ONLY
    if not dag_path.hasFn(om.MFn.kMesh):
        om.MGlobal.displayError("Selection is not a Mesh. Geometry saving skipped.")
        return

    # Get Names
    fn_mesh = om.MFnMesh(dag_path)
    shape_name = fn_mesh.name()

    dag_path.pop()
    fn_trans = om.MFnDependencyNode(dag_path.node())
    trans_name = fn_trans.name()

    # Get Parent
    fn_dag = om.MFnDagNode(dag_path)
    parent_obj = fn_dag.parent(0)
    parent_name = None
    if not parent_obj.hasFn(om.MFn.kWorld):
        parent_name = om.MFnDependencyNode(parent_obj).name()

    # Extract Mesh Data
    dag_path.extendToShape()

    points = fn_mesh.getPoints(om.MSpace.kObject)
    counts, connects = fn_mesh.getVertices()

    # Dictionary for JSON
    data = {
        "version": "1.3",
        "type": "mesh",
        "transform_name": trans_name,
        "shape_name": shape_name,
        "parent_name": parent_name,
        "points": [(p.x, p.y, p.z) for p in points],
        "counts": list(counts),
        "connects": list(connects)
    }

    try:
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=4)
        om.MGlobal.displayInfo(f"Saved Mesh: {trans_name}")
    except IOError as e:
        om.MGlobal.displayError(f"IO Error: {e}")

def create_geo(file_path):
    """
    Reconstructs MESHES.

    Args:
        file_path (str): Full path to the JSON file containing mesh data.
    """
    if not os.path.exists(file_path):
        om.MGlobal.displayError("File not found.")
        return

    with open(file_path, 'r') as f:
        data = json.load(f)

    # Only Meshes
    if data.get("type") != "mesh" and "counts" not in data:
        om.MGlobal.displayError("JSON file does not contain Mesh data.")
        return

    # 1. Prepare Points
    om_points = om.MPointArray()
    for p in data['points']:
        om_points.append(om.MPoint(p[0], p[1], p[2]))

    # 2. Create Mesh
    fn_mesh = om.MFnMesh()
    om_counts = om.MIntArray(data['counts'])
    om_connects = om.MIntArray(data['connects'])

    new_transform = fn_mesh.create(om_points, om_counts, om_connects)

    # 3. Naming & Parenting
    fn_trans = om.MFnDependencyNode(new_transform)
    fn_trans.setName(data['transform_name'])
    final_trans_name = fn_trans.name()

    fn_dag = om.MFnDagNode(new_transform)
    child = fn_dag.child(0)
    fn_shape = om.MFnDependencyNode(child)
    fn_shape.setName(data['shape_name'])

    target_parent = data.get("parent_name")
    if target_parent and cmds.objExists(target_parent):
        try:
            cmds.parent(final_trans_name, target_parent)
        except:
            om.MGlobal.displayWarning(f"Could not parent to {target_parent}")

    # Adding initial shader
    cmds.sets(final_trans_name, edit=True, forceElement="initialShadingGroup")
    om.MGlobal.displayInfo(f"Reconstructed Mesh: {final_trans_name}")
    return final_trans_name

class SkinIO:
    def __init__(self):
        self.k_skin_attrs = [
            "skinningMethod", "normalizeWeights",
            "maintainMaxInfluences", "maxInfluences", "weightDistribution"
        ]
        self.tolerance = 1e-5

    def _get_dag_path(self, node_name):
        """Helper to get MDagPath from name (For Geometry)."""
        sel = om.MSelectionList()
        try:
            sel.add(node_name)
            return sel.getDagPath(0)
        except:
            return None

    def _get_mobject(self, node_name):
        """Helper to get MObject from name (For SkinClusters/DG Nodes)."""
        sel = om.MSelectionList()
        try:
            sel.add(node_name)
            return sel.getDependNode(0)
        except:
            return None

    def _get_skin_clusters(self, dag_path):
        """Helper to get all skin clusters connected to a DAG path."""
        try:
            history = cmds.listHistory(dag_path.fullPathName(), pruneDagObjects=True, interestLevel=1) or []
            skins = [x for x in history if cmds.nodeType(x) == "skinCluster"]
            return list(reversed(skins))
        except:
            return []

    def _get_geometry_components(self, dag_path):
        """
        Returns (count, MObject_Component) for Mesh, Curve, or Surface.
        Handles Single vs Double Indexed components.
        """
        component = None
        count = 0
        
        # 1. Mesh (Single Indexed)
        if dag_path.hasFn(om.MFn.kMesh):
            fn_mesh = om.MFnMesh(dag_path)
            count = fn_mesh.numVertices
            
            fn_single = om.MFnSingleIndexedComponent()
            component = fn_single.create(om.MFn.kMeshVertComponent)
            fn_single.setCompleteData(count)
            
        # 2. Curve (Single Indexed)
        elif dag_path.hasFn(om.MFn.kNurbsCurve):
            fn_curve = om.MFnNurbsCurve(dag_path)
            count = fn_curve.numCVs
            
            fn_single = om.MFnSingleIndexedComponent()
            component = fn_single.create(om.MFn.kCurveCVComponent)
            fn_single.setCompleteData(count)
            
        # 3. Surface (Double Indexed - U, V)
        elif dag_path.hasFn(om.MFn.kNurbsSurface):
            fn_surf = om.MFnNurbsSurface(dag_path)
            num_u = fn_surf.numCVsInU
            num_v = fn_surf.numCVsInV
            count = num_u * num_v
            
            fn_double = om.MFnDoubleIndexedComponent()
            component = fn_double.create(om.MFn.kSurfaceCVComponent)
            fn_double.setCompleteData(num_u, num_v)
            
        return count, component

    def _get_geometry_from_skin(self, skin_mobj):
        """Finds any connected Mesh, Curve, or Surface."""
        try:
            fn_skin = oma.MFnSkinCluster(skin_mobj)
            geoms = fn_skin.getOutputGeometry()
            found_paths = []

            for i in range(len(geoms)):
                node = geoms[i]
                if (node.hasFn(om.MFn.kMesh) or
                    node.hasFn(om.MFn.kNurbsCurve) or
                    node.hasFn(om.MFn.kNurbsSurface)):

                    fn_dag = om.MFnDagNode(node)
                    if not fn_dag.isIntermediateObject:
                        found_paths.append(fn_dag.getPath())
            return found_paths
        except:
            return []

    def export_skins(self, file_path):
        """
        Exports skin cluster data for selected geometry or entire scene.
        """
        om.MGlobal.displayInfo(f"--- Exporting Skins to: {file_path} ---")
        sel = om.MGlobal.getActiveSelectionList()
        meshes_map = {}

        if sel.length() > 0:
            it_sel = om.MItSelectionList(sel)
            while not it_sel.isDone():
                obj = it_sel.getDependNode()

                # SkinCluster Selected
                if obj.hasFn(om.MFn.kSkinClusterFilter):
                    paths = self._get_geometry_from_skin(obj)
                    for p in paths: meshes_map[p.fullPathName()] = p

                # Transform or Shape Selected
                elif obj.hasFn(om.MFn.kDependencyNode):
                    try:
                        path = it_sel.getDagPath()
                        if path.node().hasFn(om.MFn.kTransform):
                            path.extendToShape()

                        # Check 3 types
                        node = path.node()
                        if (node.hasFn(om.MFn.kMesh) or
                            node.hasFn(om.MFn.kNurbsCurve) or
                            node.hasFn(om.MFn.kNurbsSurface)):

                             if not om.MFnDagNode(path).isIntermediateObject:
                                meshes_map[path.fullPathName()] = path
                    except:
                        pass
                it_sel.next()

        else:
            it_dep = om.MItDependencyNodes(om.MFn.kSkinClusterFilter)
            while not it_dep.isDone():
                paths = self._get_geometry_from_skin(it_dep.thisNode())
                for p in paths: meshes_map[p.fullPathName()] = p
                it_dep.next()

        if not meshes_map:
            om.MGlobal.displayWarning("No skinned geometry found.")
            return

        full_data = {}
        meshes_to_process = list(meshes_map.values())

        for geo_path in meshes_to_process:
            geo_name = geo_path.partialPathName()

            # Get Components (Mesh, Curve, Surface)
            vtx_count, vertex_comp = self._get_geometry_components(geo_path)

            if vtx_count == 0 or vertex_comp is None: 
                continue

            skins = self._get_skin_clusters(geo_path)
            if not skins: continue

            # Uses MObject.apiTypeStr (API 2.0)
            om.MGlobal.displayInfo(f"Processing: {geo_name} | Type: {geo_path.node().apiTypeStr} | Points: {vtx_count}")

            geo_skin_data = []

            for skin_name in skins:
                sel_skin = om.MSelectionList()
                sel_skin.add(skin_name)
                mf_skin = oma.MFnSkinCluster(sel_skin.getDependNode(0))

                attrs = {attr: cmds.getAttr(f"{skin_name}.{attr}") for attr in self.k_skin_attrs if cmds.attributeQuery(attr, n=skin_name, ex=True)}

                influences_paths = mf_skin.influenceObjects()
                inf_names = [p.partialPathName() for p in influences_paths]

                # Get Weights (SAFE WRAPPED)
                try:
                    weights_marray, _ = mf_skin.getWeights(geo_path, vertex_comp)
                except RuntimeError as e:
                    om.MGlobal.displayError(f"Failed to get weights for {geo_name} ({skin_name}): {e}")
                    continue

                flat_weights = list(weights_marray)
                sparse_weights = {}
                stride = len(inf_names)

                for inf_idx, inf_name in enumerate(inf_names):
                    inf_vals = flat_weights[inf_idx::stride]
                    j_indices = [i for i, v in enumerate(inf_vals) if v > self.tolerance]
                    j_weights = [round(inf_vals[i], 5) for i in j_indices]

                    if j_indices:
                        sparse_weights[inf_name] = {"ix": j_indices, "vw": j_weights}

                # Blend Weights (DQ)
                sparse_blend = {}
                try:
                    blend_weights_marray = mf_skin.getBlendWeights(geo_path, vertex_comp)
                    flat_blend = list(blend_weights_marray)
                    b_indices = [i for i, v in enumerate(flat_blend) if v > self.tolerance]
                    b_values = [round(flat_blend[i], 5) for i in b_indices]
                    if b_indices:
                        sparse_blend = {"ix": b_indices, "vw": b_values}
                except:
                    pass

                skin_entry = {
                    "name": skin_name,
                    "vertex_count": vtx_count,
                    "attributes": attrs,
                    "influences": inf_names,
                    "sparse_weights": sparse_weights,
                    "sparse_blend": sparse_blend
                }
                geo_skin_data.append(skin_entry)

            full_data[geo_name] = geo_skin_data

        with open(file_path, 'w') as f:
            json.dump(full_data, f, separators=(',', ':'))

        om.MGlobal.displayInfo("Export completed.")

    def import_skins(self, file_path):
        """
        Imports skin cluster data from JSON file.
        """
        if not os.path.exists(file_path):
            om.MGlobal.displayError("File not found.")
            return

        with open(file_path, 'r') as f:
            data = json.load(f)

        for geo_name, skins_list in data.items():
            geo_path = self._get_dag_path(geo_name)
            if not geo_path:
                om.MGlobal.displayWarning(f"Geometry missing: {geo_name}")
                continue

            geo_path.extendToShape()

            # Get Components (Mesh, Curve, Surface)
            current_vtx_count, vertex_comp = self._get_geometry_components(geo_path)

            if current_vtx_count == 0:
                om.MGlobal.displayWarning(f"Skipping {geo_name}: Not a Mesh, Curve, or Surface.")
                continue

            processed_skins = []

            for skin_data in skins_list:
                skin_name = skin_data["name"]
                target_vtx_count = skin_data["vertex_count"]

                if current_vtx_count != target_vtx_count:
                    om.MGlobal.displayError(f"Topology mismatch {skin_name}: JSON:{target_vtx_count} vs Scene:{current_vtx_count}")
                    continue

                json_influences = skin_data["influences"]

                # Create or Retrieve SkinCluster
                if cmds.objExists(skin_name) and cmds.nodeType(skin_name) == "skinCluster":
                    skin_mobj = self._get_mobject(skin_name)
                    mf_skin = oma.MFnSkinCluster(skin_mobj)
                    
                    scene_infs = [p.partialPathName() for p in mf_skin.influenceObjects()]
                    missing = [x for x in json_influences if x not in scene_infs]
                    if missing:
                        cmds.skinCluster(skin_name, e=True, addInfluence=missing, weight=0.0)
                else:
                    valid_joints = [j for j in json_influences if cmds.objExists(j)]
                    if not valid_joints:
                        om.MGlobal.displayWarning(f"No valid joints found for {skin_name}")
                        continue

                    # Create new skin
                    try:
                         # Using toSelectedBones is safer for complex hierarchies
                        new_skin = cmds.skinCluster(valid_joints, geo_path.fullPathName(), n=skin_name, toSelectedBones=True)[0]
                    except:
                        # Fallback for simple joints
                        new_skin = cmds.skinCluster(valid_joints, geo_path.fullPathName(), n=skin_name)[0]

                    # FIXED: Get MObject (DependNode) for SkinCluster, NOT DagPath
                    skin_mobj = self._get_mobject(new_skin)
                    mf_skin = oma.MFnSkinCluster(skin_mobj)

                # Set Attrs
                for attr, val in skin_data["attributes"].items():
                    try: cmds.setAttr(f"{skin_name}.{attr}", val)
                    except: pass

                # Map Influences
                scene_inf_paths = mf_skin.influenceObjects()
                scene_inf_names = [p.partialPathName() for p in scene_inf_paths]
                scene_inf_map = {name: i for i, name in enumerate(scene_inf_names)}
                num_scene_infs = len(scene_inf_names)

                # Reconstruct Weights
                full_weight_list = [0.0] * (current_vtx_count * num_scene_infs)

                for j_name, data_block in skin_data.get("sparse_weights", {}).items():
                    if j_name not in scene_inf_map: continue
                    inf_idx = scene_inf_map[j_name]
                    for v_idx, weight in zip(data_block["ix"], data_block["vw"]):
                        flat_index = (v_idx * num_scene_infs) + inf_idx
                        full_weight_list[flat_index] = weight

                # Apply Weights
                m_indices = om.MIntArray(list(range(num_scene_infs)))
                m_weights = om.MDoubleArray(full_weight_list)

                cmds.setAttr(f"{skin_name}.normalizeWeights", 0)
                mf_skin.setWeights(geo_path, vertex_comp, m_indices, m_weights, False)
                cmds.setAttr(f"{skin_name}.normalizeWeights", 1)

                # Apply Blend Weights
                sparse_blend = skin_data.get("sparse_blend", {})
                if sparse_blend:
                    full_blend = [0.0] * current_vtx_count
                    for v_idx, val in zip(sparse_blend["ix"], sparse_blend["vw"]):
                        full_blend[v_idx] = val
                    mf_skin.setBlendWeights(geo_path, vertex_comp, om.MDoubleArray(full_blend))

                processed_skins.append(skin_name)

            # Reorder Stack
            if processed_skins:
                hist = cmds.listHistory(geo_path.fullPathName(), pruneDagObjects=True, interestLevel=1)
                curr_skins = [x for x in reversed(hist) if cmds.nodeType(x) == "skinCluster"]

create_geo("C:/tmp/skin_data.json")