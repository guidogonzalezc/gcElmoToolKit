import maya.cmds as cmds
import maya.api.OpenMaya as om
import math

class SmartOffsetBaker:
    def __init__(self):
        # Dictionary to hold our calculated offset matrices: { "ctl_name": MMatrix }
        self.cached_offsets = {}
        self.reference_ctl = None

    def get_namespace(self, node):
        if ":" in node:
            return node.rsplit(":", 1)[0]
        return ""

    def get_target_ctls(self, namespace):
        search_str = f"{namespace}:*_CTL" if namespace else "*_CTL"
        all_ctls = cmds.ls(search_str, type="transform") or []
        
        valid_ctls = []
        for ctl in all_ctls:
            has_trans = cmds.attributeQuery("TranslateValue", node=ctl, exists=True)
            has_rot = cmds.attributeQuery("RotateValue", node=ctl, exists=True)
            
            if has_trans or has_rot:
                try:
                    t_val = cmds.getAttr(f"{ctl}.TranslateValue") if has_trans else None
                    r_val = cmds.getAttr(f"{ctl}.RotateValue") if has_rot else None
                    
                    if t_val == 0 or r_val == 0:
                        valid_ctls.append(ctl)
                except Exception:
                    pass
                    
        return valid_ctls

    def store_positions(self):
        """Step 1: Calculate the offset matrix between the IK CTLs and the selected Body CTL."""
        sel = cmds.ls(selection=True)
        if not sel:
            om.MGlobal.displayWarning("Select the 'Body' or 'Parent' controller to act as the reference.")
            return

        self.reference_ctl = sel[0]
        ns = self.get_namespace(self.reference_ctl)
        ctls = self.get_target_ctls(ns)

        if not ctls:
            om.MGlobal.displayWarning(f"No valid _CTLs found in namespace '{ns}'.")
            return

        # Get the World Matrix of the Reference (Body) and invert it
        ref_mat_list = cmds.getAttr(f"{self.reference_ctl}.worldMatrix[0]")
        ref_mmat = om.MMatrix(ref_mat_list)
        ref_inv_mmat = ref_mmat.inverse()

        self.cached_offsets.clear()
        
        for ctl in ctls:
            if ctl == self.reference_ctl:
                continue # Skip the body controller itself
                
            # Get IK CTL world matrix
            ctl_mat_list = cmds.getAttr(f"{ctl}.worldMatrix[0]")
            ctl_mmat = om.MMatrix(ctl_mat_list)
            
            # Calculate the Offset Matrix: Child * ParentInverse
            offset_mmat = ctl_mmat * ref_inv_mmat
            self.cached_offsets[ctl] = offset_mmat
        
        om.MGlobal.displayInfo(f"Stored offsets for {len(self.cached_offsets)} IK controllers relative to {self.reference_ctl}.")

    def snap_and_key(self):
        """Step 2: Reapply the stored offsets based on the reference controller's NEW position."""
        if not self.cached_offsets or not self.reference_ctl:
            om.MGlobal.displayWarning("No offsets stored. Run store_positions() first.")
            return
            
        if not cmds.objExists(self.reference_ctl):
            om.MGlobal.displayWarning("Reference controller no longer exists!")
            return

        # Get the NEW World Matrix of the Reference (Body)
        new_ref_mat_list = cmds.getAttr(f"{self.reference_ctl}.worldMatrix[0]")
        new_ref_mmat = om.MMatrix(new_ref_mat_list)
        
        for ctl, offset_mmat in self.cached_offsets.items():
            if cmds.objExists(ctl):
                
                # 1. Calculate the New World Matrix
                # $NewWorld = Offset \times NewReferenceWorld$
                new_world_mmat = offset_mmat * new_ref_mmat
                
                # 2. Get the controller's parent inverse matrix
                parent_inv_list = cmds.getAttr(f"{ctl}.parentInverseMatrix[0]")
                parent_inv_mmat = om.MMatrix(parent_inv_list)
                
                # 3. Calculate the New Local Matrix
                # $LocalMatrix = NewWorldMatrix \times ParentInverseMatrix$
                new_local_mmat = new_world_mmat * parent_inv_mmat
                
                # 4. Decompose the LOCAL matrix
                trans_matrix = om.MTransformationMatrix(new_local_mmat)
                
                # Extract Translation (Now in Local Space)
                pos = trans_matrix.translation(om.MSpace.kTransform)
                
                # Extract Rotation matching the CTL's rotate order
                rot_order = cmds.getAttr(f"{ctl}.rotateOrder")
                trans_matrix.reorderRotation(rot_order + 1)
                euler_rot = trans_matrix.rotation(asQuaternion=False)
                
                rx = math.degrees(euler_rot.x)
                ry = math.degrees(euler_rot.y)
                rz = math.degrees(euler_rot.z)
                
                try:
                    # 5. Set attributes directly instead of using xform
                    cmds.setAttr(f"{ctl}.translate", pos.x, pos.y, pos.z)
                    cmds.setAttr(f"{ctl}.rotate", rx, ry, rz)
                    
                    cmds.setKeyframe(ctl, attribute=['translate', 'rotate'])
                except RuntimeError as e:
                    om.MGlobal.displayWarning(f"Could not fully snap {ctl}. Error: {e}")
        
        om.MGlobal.displayInfo(f"IK Controllers snapped to maintain offset with {self.reference_ctl} and keyed.")

# global_baker = SmartOffsetBaker()

# global_baker.store_positions()

global_baker.snap_and_key()