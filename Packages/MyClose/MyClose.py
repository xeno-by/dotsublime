import sublime, sublime_plugin

class MyCloseCommand(sublime_plugin.WindowCommand):
  def run(self):
    if self.window.views():
      self.window.run_command("close")
    else:
      pass
