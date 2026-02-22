import maya.utils as mu
import maya.cmds as cmds
import getpass, os, json


"""
This script sets up the Maya environment by creating command ports and loading the Puiastre Productions UI.
It also executes a deferred command to load the UI after Maya has fully initialized.
"""

def open_vs_code_ports():
    if not cmds.commandPort(":4434", query=True):
        cmds.commandPort(name=":4434")
    if not cmds.commandPort("localhost:7001", query=True):
        cmds.commandPort(name="localhost:7001")

def init_elmo_ui():
    try:
        import elmoTools.ui.option_menu as option_menu
        option_menu.elmo_ui()
        print("Elmo UI loaded successfully.")
    except ImportError as e:
        cmds.warning(f"Could not load Elmo UI: {e}")
    open_vs_code_ports()


def plugin_loader():
    if not cmds.pluginInfo("AdonisFX", query=True, loaded=True):
        cmds.unloadPlugin("AdonisFX")
        cmds.loadPlugin("AdonisFX")
    else:
        cmds.loadPlugin("AdonisFX")

mu.executeDeferred(init_elmo_ui)

plugin_loader()

