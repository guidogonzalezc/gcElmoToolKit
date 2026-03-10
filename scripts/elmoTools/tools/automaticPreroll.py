import maya.cmds as cmds
import maya.api.OpenMaya as om
import math

class SmartOffsetBaker:
    def __init__(self):
        # Hold calculated offset matrices
        self.cached_offsets = {}
        self.reference_ctl = None
        self.layer_name = "Preroll_Baked_Layer"

        # Frame setup
        self.start_time = 1000 
        self.sample_frame = self.start_time + 5    
        self.move_start = self.start_time - 5      # 995
        self.blend_frame = 980                 
        self.inertia_rest = 960                
        self.default_rest = 930      

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
        """Force T-Pose and explicitly add attributes to the layer to avoid warnings."""
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

            if attrs_to_key: 
                # Register attributes to the layer before keying to prevent warnings
                for attr in attrs_to_key:
                    try:
                        cmds.animLayer(self.layer_name, edit=True, attribute=f"{ctrl}.{attr}")
                    except: pass
                
                cmds.setKeyframe(ctrl, attribute=attrs_to_key, time=self.default_rest, animLayer=self.layer_name)

        cmds.xform(self.reference_ctl, ws=True, m=self.calculate_intertia(-5.0))
        
        # Ensure reference ctl transforms are in the layer
        for attr in ['tx','ty','tz','rx','ry','rz']:
            try: cmds.animLayer(self.layer_name, edit=True, attribute=f"{self.reference_ctl}.{attr}")
            except: pass
            
        cmds.setKeyframe(self.reference_ctl, at=['tx','ty','tz','rx','ry','rz'], time=self.inertia_rest, animLayer=self.layer_name)

    def calculate_intertia(self, frames_offset=5.0):
        cmds.currentTime(self.start_time, edit=True, update=True)
        tf_1000 = om.MTransformationMatrix(om.MMatrix(cmds.xform(self.reference_ctl, q=True, ws=True, m=True)))
        
        cmds.currentTime(self.sample_frame, edit=True, update=True)
        tf_1005 = om.MTransformationMatrix(om.MMatrix(cmds.xform(self.reference_ctl, q=True, ws=True, m=True)))

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

        return list(tf_target.asMatrix())

    def inertia_pose(self):
        """Set the active layer explicitly to safely copy/paste keys without flag errors."""
        # Deselect all layers, make ours active
        for layer in cmds.ls(type="animLayer"):
            cmds.animLayer(layer, edit=True, selected=False)
        cmds.animLayer(self.layer_name, edit=True, selected=True)

        copied_keys = cmds.copyKey(self.all_ctls, time=(self.start_time, self.start_time))

        if copied_keys:
            cmds.pasteKey(self.all_ctls, time=(self.blend_frame, self.blend_frame), option="insert")

            cmds.xform(self.reference_ctl, ws=True, m=self.calculate_intertia(-5.0))
            cmds.setKeyframe(self.reference_ctl, at=['tx','ty','tz','rx','ry','rz'], time=self.blend_frame, animLayer=self.layer_name)

    def _lineal_animation(self):
        """Directly targets the animCurves of the layer. Bypasses buggy string flags."""
        layer_curves = cmds.animLayer(self.layer_name, query=True, animCurves=True)
        
        if layer_curves:
            # Running keyTangent directly on curve nodes is ultra-fast and ignores other layers
            cmds.keyTangent(layer_curves, time=(self.default_rest, self.start_time), lock=False)
            cmds.keyTangent(layer_curves, time=(self.default_rest, self.start_time), inTangentType="linear", outTangentType="linear")
            om.MGlobal.displayInfo("Tangents converted to linear.")
            
    def create_baked_layer(self):
        end_time = cmds.findKeyframe(self.all_ctls, which='last')
        if not end_time or end_time < self.start_time:
            end_time = self.start_time + 10 
            
        end_time = int(math.ceil(end_time))
            
        if cmds.objExists(self.layer_name):
            cmds.delete(self.layer_name)
            
        cmds.animLayer(self.layer_name, override=True)
        
        cmds.select(self.all_ctls, replace=True)
        cmds.animLayer(self.layer_name, edit=True, addSelectedObjects=True)
        cmds.select(clear=True)
            
        om.MGlobal.displayInfo(f"Baking animation to {self.layer_name} from {self.start_time} to {end_time}...")
        
        cmds.bakeResults(
            self.all_ctls,
            simulation=True, 
            time=(self.start_time, end_time),
            destinationLayer=self.layer_name,
            sampleBy=1,
            disableImplicitControl=True,
            minimizeRotation=True
        )

    def store_positions(self, time_code):
        cmds.currentTime(time_code, edit=True, update=True)
        
        ref_mat_list = cmds.getAttr(f"{self.reference_ctl}.worldMatrix[0]")
        ref_mmat = om.MMatrix(ref_mat_list)
        ref_inv_mmat = ref_mmat.inverse()

        self.cached_offsets.clear()
        
        for ctl in self.ctls:
            if ctl == self.reference_ctl:
                continue 
                
            ctl_mat_list = cmds.getAttr(f"{ctl}.worldMatrix[0]")
            ctl_mmat = om.MMatrix(ctl_mat_list)
            
            offset_mmat = ctl_mmat * ref_inv_mmat
            self.cached_offsets[ctl] = offset_mmat

    def snap_and_key(self, time_code):
        cmds.currentTime(time_code, edit=True, update=True)

        if not self.cached_offsets or not self.reference_ctl:
            return
            
        if not cmds.objExists(self.reference_ctl):
            return

        new_ref_mat_list = cmds.getAttr(f"{self.reference_ctl}.worldMatrix[0]")
        new_ref_mmat = om.MMatrix(new_ref_mat_list)
        
        for ctl, offset_mmat in self.cached_offsets.items():
            if cmds.objExists(ctl):
                
                new_world_mmat = offset_mmat * new_ref_mmat
                
                parent_inv_list = cmds.getAttr(f"{ctl}.parentInverseMatrix[0]")
                parent_inv_mmat = om.MMatrix(parent_inv_list)
                
                new_local_mmat = new_world_mmat * parent_inv_mmat
                
                trans_matrix = om.MTransformationMatrix(new_local_mmat)
                pos = trans_matrix.translation(om.MSpace.kTransform)
                
                rot_order = cmds.getAttr(f"{ctl}.rotateOrder")
                trans_matrix.reorderRotation(rot_order + 1)
                euler_rot = trans_matrix.rotation(asQuaternion=False)
                
                rx = math.degrees(euler_rot.x)
                ry = math.degrees(euler_rot.y)
                rz = math.degrees(euler_rot.z)
                
                try:
                    cmds.setAttr(f"{ctl}.translate", pos.x, pos.y, pos.z)
                    cmds.setAttr(f"{ctl}.rotate", rx, ry, rz)
                    
                    cmds.setKeyframe(ctl, attribute=['translate', 'rotate'], time=time_code, animLayer=self.layer_name)
                except RuntimeError:
                    pass

    def make(self):
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

        # Wrapped in Undo Chunk for safety
        cmds.undoInfo(openChunk=True, chunkName="AutoPreroll_Setup")
        try:
            self.create_baked_layer()
            self.set_t_pose()
            self.store_positions(self.default_rest)
            self.snap_and_key(self.inertia_rest)
            self.inertia_pose()
            self.store_positions(self.start_time)
            self.snap_and_key(self.blend_frame)
            self._lineal_animation()
            
            om.MGlobal.displayInfo("Preroll successfully built on Override Layer!")
        except Exception as e:
            om.MGlobal.displayError(f"Preroll generation failed: {e}")
        finally:
            cmds.undoInfo(closeChunk=True)

# Run Setup
global_baker = SmartOffsetBaker()
global_baker.make()