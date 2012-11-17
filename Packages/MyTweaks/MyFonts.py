import sublime, sublime_plugin

class MySmallerFontCommand(sublime_plugin.WindowCommand):
  def run(self):
    self.window.run_command("decrease_font_size")

class MyBiggerFontCommand(sublime_plugin.WindowCommand):
  def run(self):
    self.window.run_command("increase_font_size")