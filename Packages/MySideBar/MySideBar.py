import sublime, sublime_plugin

class MyRevealInSideBar(sublime_plugin.WindowCommand):
  def run(self):
    window = self.window
    window.run_command("reveal_in_side_bar")
    window.run_command("focus_side_bar")
    window.run_command("move", { "by": "lines", "forward": False })
    window.run_command("move", { "by": "lines", "forward": True })

