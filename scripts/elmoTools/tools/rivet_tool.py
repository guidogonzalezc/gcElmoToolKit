import maya.cmds as cmds
import maya.api.OpenMaya as om2
import maya.cmds as cmds
import maya.api.OpenMayaAnim as om2a
import re

class RivetTool(object):
    """
    Utility to create rivets on meshes using matrix constraints.
    """
    def __init__(self):
        pass

    def _check_name_exists(self, name):
        """
        Checks if a node with the given name already exists in the scene.

        Args:
            name: The name to check for existence.

        Returns:
            True if a node with the name exists, False otherwise.
        """
        
        
        # If it doesn't exist, return as is
        if not cmds.objExists(name):
            return name

        # Split name into base and trailing numbers
        match = re.search(r"^(.*?)(\d+)$", name)
        if match:
            base = match.group(1)
            padding = len(match.group(2))
            index = int(match.group(2))
        else:
            base = name
            padding = 1
            index = 0

        # Increment until a unique name is found
        new_name = name
        while cmds.objExists(new_name):
            index += 1
            new_name = f"{base}{str(index).zfill(padding)}"
            
        return new_name


    def create_rivet(self, threshold=1e-5, name="muscleJiggleRivet"):
        """
        Creates a rivet based on the current selection (Edge or Point).

        Args:
            threshold: 
        """

        sel = om2.MGlobal.getActiveSelectionList()
        if sel.isEmpty():
            om2.MGlobal.displayError("Selection is empty.")
            return

        # Only support single component selection for now
        path, comp = sel.getComponent(0)
        if comp.isNull() or comp.apiType() != om2.MFn.kMeshVertComponent:
            om2.MGlobal.displayError("Please select mesh vertices.")
            return

        it_graph = om2.MItDependencyGraph(
            path.node(), om2.MFn.kSkinClusterFilter,
            om2.MItDependencyGraph.kUpstream, om2.MItDependencyGraph.kDepthFirst, om2.MItDependencyGraph.kNodeLevel
        )

        # Get all SkinClusters
        skin_clusters = []
        while not it_graph.isDone():
            skin_clusters.append(it_graph.currentNode())
            it_graph.next()

        if not skin_clusters:
            om2.MGlobal.displayWarning("No SkinClusters found in the history. No rivet will be created.")
            return

        skin_clusters.reverse()
        
        fn_comp = om2.MFnSingleIndexedComponent(comp)
        vertex_indices = fn_comp.getElements()
        mesh_name = path.partialPathName()
        mesh_fn = om2.MFnMesh(path)

        joint_delta_nodes = {}
        created_trackers = []

        # 1. Process Vertices
        for i, vtx_id in enumerate(vertex_indices):
            
            vtx_iter = om2.MItMeshVertex(path)

            pt = mesh_fn.getPoint(vtx_id, om2.MSpace.kWorld)
            x_val = list(pt)[0]

            if abs(x_val) < 1e-3:
                side = "C"
            elif x_val > 0:
                side = "L"
            else:
                side = "R"            
            

            name_check = self._check_name_exists(f"{side}_{name}0{i}_MMX")
            mult_node = cmds.createNode("multMatrix", name=name_check, ss=True)
            created_trackers.append(mult_node)
                        
            # 1. Primary Axis: Vertex Normal (X-axis)
            normal = mesh_fn.getVertexNormal(vtx_id, False, om2.MSpace.kWorld)
            x_axis = om2.MVector(normal).normal()
            
            # 2. Find the most vertical Edge Flow
            vtx_iter.setIndex(vtx_id)
            connected_verts = vtx_iter.getConnectedVertices()
            
            best_edge = om2.MVector()
            max_y_dot = -1.0
            world_y = om2.MVector(0, 1, 0)
            
            # Evaluate all connected edges to find the one closest to vertical
            for neighbor_id in connected_verts:
                neighbor_pt = mesh_fn.getPoint(neighbor_id, om2.MSpace.kWorld)
                edge_vec = (om2.MVector(neighbor_pt) - om2.MVector(pt)).normal()
                
                # Use absolute value to judge the line of action, regardless of direction
                y_dot = abs(edge_vec * world_y)
                if y_dot > max_y_dot:
                    max_y_dot = y_dot
                    best_edge = edge_vec
                    
            # 3. Enforce "Up" Direction (Flip if pointing down)
            # If the true dot product is less than 0, the edge is pointing downwards.
            if (best_edge * world_y) < 0.0:
                best_edge = best_edge * -1.0
                
            # Singularity fallback
            if abs(x_axis * best_edge) > 0.999:
                best_edge = world_y
                
            # 4. Orthogonalize the axes
            # Z is perpendicular to the normal and the oriented edge flow
            z_axis = (x_axis ^ best_edge).normal()
            
            # Y is tangent to the surface, follows edge flow, and aims UP
            y_axis = (z_axis ^ x_axis).normal()
            
            # Construct the 4x4 offset matrix
            vtx_bind_matrix = [
                x_axis.x, x_axis.y, x_axis.z, 0.0,
                y_axis.x, y_axis.y, y_axis.z, 0.0,
                z_axis.x, z_axis.y, z_axis.z, 0.0,
                pt.x,     pt.y,     pt.z,     1.0
            ]
                
            cmds.setAttr(f"{mult_node}.matrixIn[0]", vtx_bind_matrix, type="matrix")

            # 2. Process SkinClusters
            for skin_idx, skin_node in enumerate(skin_clusters):
                skin_fn = om2a.MFnSkinCluster(skin_node)
                skin_name = om2.MFnDependencyNode(skin_node).name()
                
                inf_paths = skin_fn.influenceObjects()
                inf_names = [p.partialPathName() for p in inf_paths]
                
                single_vtx_comp = om2.MFnSingleIndexedComponent().create(om2.MFn.kMeshVertComponent)
                om2.MFnSingleIndexedComponent(single_vtx_comp).addElement(vtx_id)
                weights, _ = skin_fn.getWeights(path, single_vtx_comp)
                
                skin_name_wtadd = skin_name.split('_')[1] if len(skin_name.split('_')) > 1 else skin_name

                wt_add_node_name = self._check_name_exists(f"{side}_{name}{skin_name_wtadd}0{skin_idx}_WTADD")
                wt_add_node = cmds.createNode("wtAddMatrix", name=wt_add_node_name, ss=True)
                
                wt_idx = 0
                for j in range(len(inf_names)):
                    w = weights[j]
                    if w >= threshold:
                        jnt = inf_names[j]
                        
                        if jnt not in joint_delta_nodes:
                            delta_name = (jnt.split('_')[1] if len(jnt.split('_')) > 1 else jnt).upper()      

                            delta_node_name = self._check_name_exists(f"{side}_{name}Delta{delta_name}_MMX")
                            delta_node = cmds.createNode("multMatrix", name=delta_node_name, ss=True)
                            bind_pre = cmds.getAttr(f"{jnt}.worldInverseMatrix[0]")
                            cmds.setAttr(f"{delta_node}.matrixIn[0]", bind_pre, type="matrix")
                            cmds.connectAttr(f"{jnt}.worldMatrix[0]", f"{delta_node}.matrixIn[1]")
                            joint_delta_nodes[jnt] = delta_node
                        
                        delta_node = joint_delta_nodes[jnt]
                        cmds.connectAttr(f"{delta_node}.matrixSum", f"{wt_add_node}.wtMatrix[{wt_idx}].matrixIn")
                        cmds.setAttr(f"{wt_add_node}.wtMatrix[{wt_idx}].weightIn", w)
                        
                        wt_idx += 1
                
                target_mult_idx = skin_idx + 1
                cmds.connectAttr(f"{wt_add_node}.matrixSum", f"{mult_node}.matrixIn[{target_mult_idx}]")


            name_check = self._check_name_exists(f"{side}_{name}0{i}_CTL")

            
            # neg = cmds.createNode("transform", name=name_check.replace("_CTL", "_NEG"), ss=True, parent=grp)
            
            # anm = cmds.createNode("transform", name=name_check.replace("_CTL", "_ANM"), ss=True, parent=neg)

            grps = []
            for attr in ["_GRP", "_NEG", "_ANM"]:
                parent = grps[-1] if grps else None
                grp = cmds.createNode("transform", name=name_check.replace("_CTL", attr), ss=True, parent=parent)
                grps.append(grp)

            
            ctl = cmds.circle(name=name_check, normal=(1, 0, 0), radius=0.5, ch=False)[0]
            cmds.parent(ctl, grps[-1])  

            cmds.connectAttr(f"{mult_node}.matrixSum", f"{grps[0]}.offsetParentMatrix")

            joint = cmds.createNode("joint", name=f"{name_check.replace('_CTL', '_JNT')}", ss=True)
            cmds.connectAttr(f"{ctl}.worldMatrix[0]", f"{joint}.offsetParentMatrix")

        
        # return created_trackers

if __name__ == "__main__":
    RivetTool().create_rivet(threshold=1e-5)
            
