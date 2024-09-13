from . import PLUGIN
import mobase  # type: ignore


def createPlugin() -> mobase.IPlugin:
    return PLUGIN.PluginTool()
