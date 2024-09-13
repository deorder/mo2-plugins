from . import merge_plugins_hide, sync_mod_order, link_deploy
import mobase  # type: ignore


def createPlugins() -> list[mobase.IPlugin]:
    return [
        merge_plugins_hide.PluginTool(),
        sync_mod_order.PluginTool(),
        link_deploy.PluginTool(),
    ]
