import sublime, sublime_plugin

class MykePrefixCommand(sublime_plugin.WindowCommand):
  def run(self):
    view = self.window.active_view()
    view.settings().set("myke_require_prefix", True)
