import maya.cmds as cmds
import maya.api.OpenMaya as om2

def transfer_multi_skin_clusters():
    """
    Transfers all skinClusters from Source to Target mesh.
    - Matches joints exactly.
    - Appends _COPY to the name.
    - Copies weights.
    - Performs a self-mirror on the result.
    """
    
    sel = cmds.ls(sl=True)
    if not sel or len(sel) != 2:
        cmds.warning("Please select exactly two meshes: Source then Target.")
        return

    source_node = sel[0]
    target_node = sel[1]

    source_shapes = cmds.listRelatives(source_node, shapes=True) or []
    target_shapes = cmds.listRelatives(target_node, shapes=True) or []
    
    if not source_shapes or not target_shapes:
        om2.MGlobal.displayError("Selection must be geometry with valid shapes.")
        return


    history = cmds.listHistory(source_shapes[0], pruneDagObjects=False, fullNodeName=True) or []
    source_skins = [node for node in history if cmds.nodeType(node) == "skinCluster"]

    source_skins.reverse()

    if not source_skins:
        om2.MGlobal.displayWarning(f"No skinClusters found on {source_node}.")
        return

    om2.MGlobal.displayInfo(f"Found {len(source_skins)} skinClusters on {source_node}. Beginning transfer...")

    for src_skin in source_skins:
        

        influences = cmds.skinCluster(src_skin, query=True, influence=True)

        new_name = f"{src_skin}_COPY"
        
        if cmds.objExists(new_name):
            om2.MGlobal.displayWarning(f"{new_name} already exists. Maya will rename it automatically.")

        om2.MGlobal.displayInfo(f"Processing: {src_skin} -> {new_name}")

        new_skin = cmds.skinCluster(
            influences, 
            target_node, 
            name=new_name, 
            toSelectedBones=False, 
            bindMethod=0, 
            normalizeWeights=1, 
            weightDistribution=0,
            mi=1,
            omi=False,
            dr=4.0,
            rui=False,
            multi=True 
        )[0]

      
        method = cmds.getAttr(f"{src_skin}.skinningMethod")
        cmds.setAttr(f"{new_skin}.skinningMethod", method)
        
     
        cmds.copySkinWeights(
            ss=src_skin, 
            ds=new_skin, 
            noMirror=True, 
            surfaceAssociation='closestPoint', 
            influenceAssociation=['label', 'oneToOne', 'closestJoint'],
            normalize=True 
        )

      
        cmds.copySkinWeights(
            ss=new_skin, 
            ds=new_skin, 
            mirrorMode='YZ', 
            surfaceAssociation='closestPoint', 
            influenceAssociation=['label', 'oneToOne'], 
            normalize=True
        )
        
        om2.MGlobal.displayInfo(f"Successfully created and mirrored: {new_skin}")

    om2.MGlobal.displayInfo("--- Transfer Complete ---")


