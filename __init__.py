from . import mergePluginsHide, syncModOrder


def createPlugins():
    return [mergePluginsHide.PluginTool(), syncModOrder.PluginTool()]
