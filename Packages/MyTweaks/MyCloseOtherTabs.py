import sublime, sublime_plugin

class MyCloseOtherTabsCommand(sublime_plugin.WindowCommand):
  def run(self):
    active_view = self.window.active_view()
    for view in self.window.views():
      if view.id() != active_view.id():
        self.window.focus_view(view)
        self.window.run_command("close_file")
