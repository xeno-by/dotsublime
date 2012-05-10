import sublime, sublime_plugin

class MykePrefixCommand(sublime_plugin.WindowCommand):
  def run(self):
    settings = sublime.load_settings("Myke.sublime-settings")
    require = settings.get("require_prefix")
    if require:
      persistent = settings.get("persistent_require_prefix")
      settings.set("persistent_require_prefix", not persistent)
    settings.set("require_prefix", True)
    sublime.save_settings("Myke.sublime-settings")
