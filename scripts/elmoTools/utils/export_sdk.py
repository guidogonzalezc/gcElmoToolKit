import maya.cmds as cmds


def get_setDrivenKey_data():
    """
    Collects animCurve* nodes that act as set driven keys (i.e. have both an input
    plug coming from some driver attribute and an output plug driving some attribute).
    Returns a list of dicts with node name, driver plugs, driven plugs, infinity/weighting
    and full key data (times, values, tangent types/angles/weights).
    """
    # gather all animCurve nodes robustly
    curves = cmds.ls(type="animCurve*") or []
    if not curves:
        # fallback: scan scene and test nodeType (safer but a bit slower)
        all_nodes = cmds.ls(long=True) or []
        curves = [n for n in all_nodes if cmds.nodeType(n).startswith("animCurve")]

    result = []

    def ensure_list(x):
        if x is None:
            return []
        if isinstance(x, (list, tuple)):
            return list(x)
        return [x]

    for c in curves:
        # which plugs feed the animCurve input (likely the driver attr)?
        driver_plugs = cmds.listConnections(c + ".input", plugs=True, source=True, destination=False) or []
        # which plugs does the animCurve output connect to (driven attrs)?
        driven_plugs = cmds.listConnections(c + ".output", plugs=True, source=False, destination=True) or []

        # we consider this an SDK if it has both a driver and at least one driven attr
        if not driver_plugs or not driven_plugs:
            continue

        curve_info = {
            "node": c,
            "drivers": driver_plugs,
            "drivens": driven_plugs,
        }

        # infinity / weighting (some curve types may not have these attrs)
        try:
            curve_info["preInfinity"] = cmds.getAttr(c + ".preInfinity")
        except Exception:
            curve_info["preInfinity"] = None
        try:
            curve_info["postInfinity"] = cmds.getAttr(c + ".postInfinity")
        except Exception:
            curve_info["postInfinity"] = None
        try:
            curve_info["weightedTangents"] = cmds.getAttr(c + ".weightedTangents")
        except Exception:
            curve_info["weightedTangents"] = False

        # key data
        times = cmds.keyframe(c, q=True, timeChange=True) or []
        values = cmds.keyframe(c, q=True, valueChange=True) or []
        inTypes = cmds.keyTangent(c, q=True, inTangentType=True) or []
        outTypes = cmds.keyTangent(c, q=True, outTangentType=True) or []
        inAngles = cmds.keyTangent(c, q=True, inAngle=True) or []
        outAngles = cmds.keyTangent(c, q=True, outAngle=True) or []
        inWeights = cmds.keyTangent(c, q=True, inWeight=True) or []
        outWeights = cmds.keyTangent(c, q=True, outWeight=True) or []
        lockFlags = cmds.keyTangent(c, q=True, lock=True) or []

        times = ensure_list(times)
        values = ensure_list(values)
        inTypes = ensure_list(inTypes)
        outTypes = ensure_list(outTypes)
        inAngles = ensure_list(inAngles)
        outAngles = ensure_list(outAngles)
        inWeights = ensure_list(inWeights)
        outWeights = ensure_list(outWeights)
        lockFlags = ensure_list(lockFlags)

        keys = []
        for i, t in enumerate(times):
            key = {
                "time": float(t),
                "value": float(values[i]) if i < len(values) else None,
                "inTangentType": inTypes[i] if i < len(inTypes) else None,
                "outTangentType": outTypes[i] if i < len(outTypes) else None,
                "inAngle": float(inAngles[i]) if i < len(inAngles) else None,
                "outAngle": float(outAngles[i]) if i < len(outAngles) else None,
                "inWeight": float(inWeights[i]) if i < len(inWeights) else None,
                "outWeight": float(outWeights[i]) if i < len(outWeights) else None,
                "lock": bool(lockFlags[i]) if i < len(lockFlags) else False,
            }
            keys.append(key)

        curve_info["keys"] = keys
        result.append(curve_info)

    return result

print(get_setDrivenKey_data())