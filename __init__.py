from . import merge_plugins_hide, sync_mod_order


def createPlugins():
    return [merge_plugins_hide.PluginTool(), sync_mod_order.PluginTool()]
