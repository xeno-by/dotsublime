import sublime, sublime_plugin

class CloseOtherTabsCommand(sublime_plugin.WindowCommand):
  def run(self):
    active_view = self.window.active_view()
    for view in self.window.views():
      if view.id() != active_view.id() and view.settings().get("repl_external_id") != "myke_console":
        self.window.focus_view(view)
        self.window.run_command("close_file")
