import json
import os
import maya.cmds as cmds
import maya.api.OpenMaya as om
import maya.api.OpenMayaAnim as oma

class SkinIO:
    def __init__(self):
        self.k_skin_attrs = [
            "skinningMethod",
            "normalizeWeights",
            "maintainMaxInfluences",
            "maxInfluences",
            "weightDistribution"
        ]
        self.tolerance = 1e-5 

    def _get_dag_path(self, node_name):
        sel = om.MSelectionList()
        try:
            sel.add(node_name)
            return sel.getDagPath(0)
        except:
            return None

    def _get_skin_clusters(self, dag_path):
        """
        Original method: Finds skins from mesh history.
        Preserved to maintain stack order export.
        """
        history = cmds.listHistory(dag_path.fullPathName(), pruneDagObjects=True, interestLevel=1) or []
        skins = [x for x in history if cmds.nodeType(x) == "skinCluster"]
        return list(reversed(skins))

    def _get_meshes_from_skin(self, skin_mobj):
        """
        New Helper: Finds the connected mesh DAG path from a SkinCluster MObject.
        """
        try:
            fn_skin = oma.MFnSkinCluster(skin_mobj)
            # getOutputGeometry returns the shapes driven by this skin
            geoms = fn_skin.getOutputGeometry()
            found_paths = []
            
            for i in range(len(geoms)):
                node = geoms[i]
                if node.hasFn(om.MFn.kMesh):
                    # Convert MObject (Node) to MDagPath
                    fn_dag = om.MFnDagNode(node)
                    path = fn_dag.getPath()
                    
                    # Ensure we are not looking at an intermediate object unless necessary
                    if not fn_dag.isIntermediateObject:
                        found_paths.append(path)
            return found_paths
        except Exception as e:
            om.MGlobal.displayWarning(f"Could not retrieve geometry from skin: {e}")
            return []

    def export_skins(self, file_path):
        om.MGlobal.displayInfo(f"--- Starting Export to: {file_path} ---")
        
        sel = om.MGlobal.getActiveSelectionList()
        
        # We use a dictionary to deduplicate meshes by their full path name
        # Key: Full Path String, Value: MDagPath Object
        meshes_map = {}

        # --- 1. SELECTION MODE ---
        if sel.length() > 0:
            # Iterate generic objects to support both Mesh and SkinCluster selection
            it_sel = om.MItSelectionList(sel)
            while not it_sel.isDone():
                obj = it_sel.getDependNode()
                
                # Case A: User selected a SkinCluster
                if obj.hasFn(om.MFn.kSkinClusterFilter):
                    paths = self._get_meshes_from_skin(obj)
                    for p in paths:
                        meshes_map[p.fullPathName()] = p
                
                # Case B: User selected a Mesh (Legacy support)
                elif obj.hasFn(om.MFn.kMesh):
                    path = it_sel.getDagPath()
                    path.extendToShape()
                    fn_dag = om.MFnDagNode(path)
                    if not fn_dag.isIntermediateObject:
                        meshes_map[path.fullPathName()] = path
                
                # Case C: User selected a Transform containing a Mesh
                elif obj.hasFn(om.MFn.kTransform):
                    # Try to extend to shape
                    try:
                        path = it_sel.getDagPath()
                        path.extendToShape()
                        if path.node().hasFn(om.MFn.kMesh):
                             meshes_map[path.fullPathName()] = path
                    except:
                        pass # Valid transform but no shape, ignore

                it_sel.next()

        # --- 2. SCENE MODE (No selection) ---
        else:
            om.MGlobal.displayInfo("No selection. Iterating all SkinClusters in scene...")
            # Use DependencyNode iterator for SkinClusters instead of DAG iterator
            it_dep = om.MItDependencyNodes(om.MFn.kSkinClusterFilter)
            while not it_dep.isDone():
                skin_obj = it_dep.thisNode()
                paths = self._get_meshes_from_skin(skin_obj)
                for p in paths:
                    meshes_map[p.fullPathName()] = p
                it_dep.next()

        if not meshes_map:
            om.MGlobal.displayWarning("No valid skinned meshes found from selection.")
            return

        # Convert map back to list for processing
        meshes_to_process = list(meshes_map.values())
        
        full_data = {}

        # --- 3. EXPORT LOOP (Preserved Logic) ---
        for mesh_path in meshes_to_process:
            mesh_name = mesh_path.partialPathName()
            mf_mesh = om.MFnMesh(mesh_path)
            vtx_count = mf_mesh.numVertices
            
            # We still find ALL skins on this mesh to ensure stack order and completeness.
            # Even if user selected just one skin, we usually want the full stack for that mesh 
            # to maintain the file format structure (Mesh -> [Skins]).
            skins = self._get_skin_clusters(mesh_path)
            if not skins:
                continue

            om.MGlobal.displayInfo(f"Processing: {mesh_name} | Skins: {len(skins)}")
            
            mesh_data = []
            
            for skin_name in skins:
                sel_skin = om.MSelectionList()
                sel_skin.add(skin_name)
                mf_skin = oma.MFnSkinCluster(sel_skin.getDependNode(0))

                # --- Atributos ---
                attrs = {}
                for attr in self.k_skin_attrs:
                    try:
                        attrs[attr] = cmds.getAttr(f"{skin_name}.{attr}")
                    except:
                        pass

                # --- Influencias ---
                influences_paths = mf_skin.influenceObjects()
                inf_names = [p.partialPathName() for p in influences_paths]

                # --- Pesos (Logica Sparse) ---
                single_comp = om.MFnSingleIndexedComponent()
                vertex_comp = single_comp.create(om.MFn.kMeshVertComponent)
                single_comp.setCompleteData(vtx_count)
                
                weights_marray, _ = mf_skin.getWeights(mesh_path, vertex_comp)
                flat_weights = list(weights_marray)
                
                sparse_weights = {}
                stride = len(inf_names)
                
                for inf_idx, inf_name in enumerate(inf_names):
                    j_indices = []
                    j_weights = []
                    
                    for v_idx in range(vtx_count):
                        val = flat_weights[v_idx * stride + inf_idx]
                        if val > self.tolerance:
                            j_indices.append(v_idx)
                            j_weights.append(round(val, 5))
                    
                    if j_indices:
                        sparse_weights[inf_name] = {
                            "ix": j_indices,
                            "vw": j_weights
                        }

                # --- Blend Weights ---
                blend_weights_marray = mf_skin.getBlendWeights(mesh_path, vertex_comp)
                flat_blend = list(blend_weights_marray)
                sparse_blend = {}
                
                b_indices = []
                b_values = []
                for v_idx, val in enumerate(flat_blend):
                    if val > self.tolerance:
                        b_indices.append(v_idx)
                        b_values.append(round(val, 5))
                
                if b_indices:
                    sparse_blend = {"ix": b_indices, "vw": b_values}
                
                skin_entry = {
                    "name": skin_name,
                    "vertex_count": vtx_count,
                    "attributes": attrs,
                    "influences": inf_names, 
                    "sparse_weights": sparse_weights,
                    "sparse_blend": sparse_blend
                }
                mesh_data.append(skin_entry)

            full_data[mesh_name] = mesh_data

        with open(file_path, 'w') as f:
            json.dump(full_data, f, separators=(',', ':'))
            
        om.MGlobal.displayInfo(f"Export completed. Optimized file saved.")

    def import_skins(self, file_path):
        # ... (Same as original import logic) ...
        # I have omitted it here for brevity as no changes were requested for import logic
        # You should keep the original import_skins code here.
        if not os.path.exists(file_path):
            om.MGlobal.displayError("JSON file does not exist.")
            return

        with open(file_path, 'r') as f:
            data = json.load(f)

        for mesh_name, skins_list in data.items():
            mesh_path = self._get_dag_path(mesh_name)
            if not mesh_path:
                om.MGlobal.displayWarning(f"Mesh skipped: {mesh_name}")
                continue
            
            mesh_path.extendToShape()
            mf_mesh = om.MFnMesh(mesh_path)
            processed_skins = []

            for skin_data in skins_list:
                skin_name = skin_data["name"]
                target_vtx_count = skin_data["vertex_count"]
                
                if mf_mesh.numVertices != target_vtx_count:
                    om.MGlobal.displayError(f"{skin_name} does not match topology. Skip.")
                    continue 

                json_influences = skin_data["influences"]
                skin_exists = cmds.objExists(skin_name) and cmds.nodeType(skin_name) == "skinCluster"
                mf_skin = None
                
                if skin_exists:
                    sel_s = om.MSelectionList()
                    sel_s.add(skin_name)
                    mf_skin = oma.MFnSkinCluster(sel_s.getDependNode(0))
                    scene_infs = [p.partialPathName() for p in mf_skin.influenceObjects()]
                    missing_infs = [inf for inf in json_influences if inf not in scene_infs]
                    if missing_infs:
                        cmds.skinCluster(skin_name, e=True, addInfluence=missing_infs, weight=0.0)
                else:
                    valid_joints = [j for j in json_influences if cmds.objExists(j)]
                    if not valid_joints: continue
                    new_skin = cmds.skinCluster(valid_joints, mesh_path.fullPathName(), n=skin_name, toSelectedBones=True, multi=True)[0]
                    sel_s = om.MSelectionList()
                    sel_s.add(new_skin)
                    mf_skin = oma.MFnSkinCluster(sel_s.getDependNode(0))

                for attr, val in skin_data["attributes"].items():
                    try:
                        cmds.setAttr(f"{skin_name}.{attr}", val)
                    except: pass
                
                scene_inf_paths = mf_skin.influenceObjects()
                scene_inf_names = [p.partialPathName() for p in scene_inf_paths]
                scene_inf_map = {name: i for i, name in enumerate(scene_inf_names)}

                num_verts = target_vtx_count
                num_scene_infs = len(scene_inf_names)

                full_weight_list = [0.0] * (num_verts * num_scene_infs)
                sparse_data = skin_data.get("sparse_weights", {})
                
                for j_name, data_block in sparse_data.items():
                    if j_name not in scene_inf_map: continue
                    scene_inf_idx = scene_inf_map[j_name]
                    indices = data_block["ix"]
                    values = data_block["vw"]
                    for v_idx, weight_val in zip(indices, values):
                        flat_index = (v_idx * num_scene_infs) + scene_inf_idx
                        full_weight_list[flat_index] = weight_val
                
                m_influence_indices = om.MIntArray(list(range(num_scene_infs)))
                final_weights = om.MDoubleArray(full_weight_list)
                
                single_comp = om.MFnSingleIndexedComponent()
                vertex_comp = single_comp.create(om.MFn.kMeshVertComponent)
                single_comp.setCompleteData(num_verts)
                
                prev_norm = cmds.getAttr(f"{skin_name}.normalizeWeights")
                prev_max = cmds.getAttr(f"{skin_name}.maintainMaxInfluences")

                cmds.setAttr(f"{skin_name}.normalizeWeights", 0)
                cmds.setAttr(f"{skin_name}.maintainMaxInfluences", 0)

                try:

                    mf_skin.setWeights(mesh_path, vertex_comp, m_influence_indices, final_weights, False)
                    
                finally:
                    cmds.setAttr(f"{skin_name}.normalizeWeights", prev_norm)
                    cmds.setAttr(f"{skin_name}.maintainMaxInfluences", prev_max)



                sparse_blend = skin_data.get("sparse_blend", {})
                if sparse_blend:
                    full_blend = [0.0] * num_verts
                    for v_idx, val in zip(sparse_blend["ix"], sparse_blend["vw"]):
                        full_blend[v_idx] = val
                    mf_skin.setBlendWeights(mesh_path, vertex_comp, om.MDoubleArray(full_blend))

                processed_skins.append(skin_name)

            if processed_skins:
                current_hist = cmds.listHistory(mesh_path.fullPathName(), pruneDagObjects=True, interestLevel=1)
                current_skins = [x for x in current_hist if cmds.nodeType(x) == "skinCluster"]
                current_skins = list(reversed(current_skins))
                unknown = [s for s in current_skins if s not in processed_skins]
                order = unknown + processed_skins
                for skin in reversed(order):
                    try: cmds.reorderDeformers(skin, mesh_path.fullPathName(), back=True)
                    except: pass

