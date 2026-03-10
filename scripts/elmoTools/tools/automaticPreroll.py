import maya.cmds as cmds
import maya.api.OpenMaya as om
import math

class SmartOffsetBaker:
    def __init__(self):

        # Hold calculated offset matrices
        self.cached_offsets = {}
        self.reference_ctl = None

        sel = cmds.ls(selection=True)

        if not sel:
            om.MGlobal.displayWarning("Select the 'Body' or 'Parent' controller to act as the reference.")
            return

        self.reference_ctl = sel[0]
        ns = self._get_namespace(self.reference_ctl)
        self.ctls, self.all_ctls = self._get_target_ctls(ns)

        if not self.ctls:
            om.MGlobal.displayWarning(f"No valid _CTLs found in namespace '{ns}'.")
            return

    def _get_namespace(self, node):
        if ":" in node:
            return node.rsplit(":", 1)[0]
        return ""

    def _get_target_ctls(self, namespace):
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
                    
        return valid_ctls, all_ctls
    
    def set_t_pose(self):
        """
        Force T-Pose on the current frame for the given controls. 
        This includes setting translation and rotation to 0, scale to 1, and any user-defined attributes to their default values.

        Args:
            ctrls (list): List of control names to set to T-Pose.

        Returns:
            None
        """
        for ctrl in self.all_ctls:
            attrs_to_key = []
            for attr in ['tx', 'ty', 'tz', 'rx', 'ry', 'rz']:
                if cmds.objExists(f"{ctrl}.{attr}") and cmds.getAttr(f"{ctrl}.{attr}", settable=True):
                    cmds.setAttr(f"{ctrl}.{attr}", 0.0)
                    attrs_to_key.append(attr)
            for attr in ['sx', 'sy', 'sz']:
                if cmds.objExists(f"{ctrl}.{attr}") and cmds.getAttr(f"{ctrl}.{attr}", settable=True):
                    cmds.setAttr(f"{ctrl}.{attr}", 1.0)
                    attrs_to_key.append(attr)
                    
            for attr in cmds.listAttr(ctrl, userDefined=True) or []:
                full_attr = f"{ctrl}.{attr}"
                if attr in ["TranslateValue","RotateValue", "switchIkFk"]: continue


                if cmds.getAttr(full_attr, settable=True):
                    try:
                        cmds.setAttr(full_attr, cmds.addAttr(full_attr, q=True, defaultValue=True))
                        attrs_to_key.append(attr)
                    except: pass

    def calculate_intertia(self, frames_offset=5.0, source_frame = 1120):
        """
        Calculate the velocity of the reference controller between the start frame and a sample frame to determine the inertia
        
        """

        # Get initial and sample positions/rotations of the reference controller to calculate velocity
        print(self.reference_ctl)
        cmds.currentTime(source_frame, edit=True)
        tf_1000 = om.MTransformationMatrix(om.MMatrix(cmds.xform(self.reference_ctl, q=True, ws=True, m=True)))
        
        cmds.currentTime(source_frame+frames_offset, edit=True)
        tf_1005 = om.MTransformationMatrix(om.MMatrix(cmds.xform(self.reference_ctl, q=True, ws=True, m=True)))

        # Calculate velocity
        pos_1000 = tf_1000.translation(om.MSpace.kWorld)
        pos_1005 = tf_1005.translation(om.MSpace.kWorld)
        vel_pos = (pos_1005 - pos_1000) / 5.0
        
        quat_1000 = tf_1000.rotation(asQuaternion=True)
        quat_1005 = tf_1005.rotation(asQuaternion=True)
        axis, angle = (quat_1000.inverse() * quat_1005).asAxisAngle()
        vel_quat = om.MQuaternion(angle / 5.0, axis)

        target_pos = pos_1000 + (vel_pos * frames_offset)
        target_quat = quat_1000 * om.MQuaternion(vel_quat.asAxisAngle()[1] * frames_offset, vel_quat.asAxisAngle()[0])
        tf_target = om.MTransformationMatrix()
        tf_target.setTranslation(target_pos, om.MSpace.kWorld)
        tf_target.setRotation(target_quat)

        matrix_list =  list(tf_target.asMatrix())
    
        locator = cmds.spaceLocator(n="temp_inertia_loc")

        cmds.xform(locator, ws=True, m=matrix_list)


    def _lineal_animation(self):
        if not isinstance(self.all_ctls, (list, tuple)):
            self.all_ctls = [self.all_ctls]

        for node in self.all_ctls:
            if not cmds.objExists(node):
                cmds.warning(f"Node '{node}' does not exist. Skipping.")
                continue

            # 1. Query to see if any keys exist in this range.
            # This prevents Maya from processing flat animCurves unnecessarily.
            keys_in_range = cmds.keyframe(node, time=(self.default_rest, self.start_time), query=True, keyframeCount=True)
            
            if not keys_in_range:
                print(f"Skip: No keys found on '{node}' between {self.default_rest} and {self.start_time}.")
                continue

            # 2. Break the tangents for all keys within the inclusive time range
            cmds.keyTangent(node, time=(self.default_rest, self.start_time), lock=False)
            
            # 3. Force the interpolation type to linear for both entry and exit of the keys
            cmds.keyTangent(node, time=(self.default_rest, self.start_time), inTangentType="linear", outTangentType="linear")
            
            print(f"Success: Converted {keys_in_range} keys to linear on '{node}' ({self.default_rest}-{self.start_time}).")
            


    def store_positions(self, time_code):
        """Step 1: Calculate the offset matrix between the IK CTLs and the selected Body CTL."""

        cmds.currentTime(time_code, edit=True, update=True)
        
        # Get the World Matrix of the Reference (Body) and invert it
        ref_mat_list = cmds.getAttr(f"{self.reference_ctl}.worldMatrix[0]")
        ref_mmat = om.MMatrix(ref_mat_list)
        ref_inv_mmat = ref_mmat.inverse()

        self.cached_offsets.clear()
        
        for ctl in self.ctls:
            if ctl == self.reference_ctl:
                continue # Skip the body controller itself
                
            # Get IK CTL world matrix
            ctl_mat_list = cmds.getAttr(f"{ctl}.worldMatrix[0]")
            ctl_mmat = om.MMatrix(ctl_mat_list)
            
            # Calculate the Offset Matrix: Child * ParentInverse
            offset_mmat = ctl_mmat * ref_inv_mmat
            self.cached_offsets[ctl] = offset_mmat
        
        om.MGlobal.displayInfo(f"Stored offsets for {len(self.cached_offsets)} IK controllers relative to {self.reference_ctl}.")

    def snap_and_key(self, time_code):
        """Step 2: Reapply the stored offsets based on the reference controller's NEW position."""

        cmds.currentTime(time_code, edit=True, update=True)


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
                    
                    cmds.setKeyframe(ctl, attribute=['translate', 'rotate'], time=time_code)
                except RuntimeError as e:
                    om.MGlobal.displayWarning(f"Could not fully snap {ctl}. Error: {e}")
        
        om.MGlobal.displayInfo(f"IK Controllers snapped to maintain offset with {self.reference_ctl} and keyed.")







global_baker = SmartOffsetBaker()
global_baker.calculate_intertia()
# global_baker.set_t_pose()

# global_baker.store_positions()

# global_baker.snap_and_key()