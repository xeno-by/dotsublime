import sublime, sublime_plugin

class MykePrefixCommand(sublime_plugin.WindowCommand):
  def run(self):
    self.window.show_input_panel("Command prefix:", "", self.prefix_input, None, None)

  def prefix_input(self, prefix):
    view = self.window.active_view()
    view.settings().set("myke_prefix", prefix)
