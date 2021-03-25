from . import merge_plugins_hide, sync_mod_order, link_deploy


def createPlugins():
    return [merge_plugins_hide.PluginTool(), sync_mod_order.PluginTool(), link_deploy.PluginTool()]
