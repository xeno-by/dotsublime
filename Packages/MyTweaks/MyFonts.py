import sublime, sublime_plugin
import re
from subprocess import call

class MyFontSizeCommand(sublime_plugin.WindowCommand):
  def __init__(self, window):
    sublime_plugin.WindowCommand.__init__(self, window)

  def camelcase_to_underscore(self, name):
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()

  def run(self):
    flavor = re.match("^My(?P<flavor>.*?)Command$", self.__class__.__name__).expand("\g<flavor>")
    self.window.run_command(self.camelcase_to_underscore(flavor))
    settings = sublime.load_settings("Preferences.sublime-settings")
    call(["growlnotify", "-a", "Sublime", "-m", "Font size has been changed to " + str(settings.get("font_size"))])

class MyIncreaseFontSizeCommand(MyFontSizeCommand):
  pass

class MyDecreaseFontSizeCommand(MyFontSizeCommand):
  pass
