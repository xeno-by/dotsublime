import sublime, sublime_plugin, os

class GotoRecentListener(sublime_plugin.EventListener):
  def on_deactivated(self, view):
    if view.file_name():
      view.window().run_command("goto_recent", { "file_name": view.file_name() })

class GotoRecentCommand(sublime_plugin.WindowCommand):
  def __init__(self, window):
    sublime_plugin.WindowCommand.__init__(self, window)
    self.recent_files = GotoRecentRecentFiles(window)
    self.enabled      = True

  def unshift(self, file_name):
    item = [os.path.basename(file_name), file_name]

    for _ in range(self.recent_files.count(item)):
      self.recent_files.remove(item)

    self.recent_files.insert(0, item)

  def selected(self, index):
    if index >= 0:
      target_file = self.recent_files[index][1]

      if self.window.active_view():
        current_file = self.window.active_view().file_name()
        if current_file:
          self.unshift(current_file)

      self.window.open_file(target_file)

    self.enabled = True

  def run(self, file_name=None):
    if self.enabled:
      if file_name:
        self.unshift(file_name)
      else:
        self.enabled = False
        self.window.show_quick_panel(list(self.recent_files), self.selected)

# Python __Underscore__ Methods
# http://www.siafoo.net/article/57
class GotoRecentRecentFiles(object):
  def __init__(self, window):
    self.window = window
    self.load()

  def project_root(self):
    # how do I reliably detect currently open project?!
    return self.window.folders()[0]

  def load(self):
    global_settings = sublime.load_settings("GotoRecent.sublime-settings")
    settings = global_settings.get(self.project_root()) or {}
    self.recent_files = settings.get("recent_files", [])

  def save(self):
    global_settings = sublime.load_settings("GotoRecent.sublime-settings")
    settings = {}
    settings["recent_files"] = self.recent_files
    global_settings.set(self.project_root(), settings)
    sublime.save_settings("GotoRecent.sublime-settings")

  def __len__(self):
    return len(self.recent_files)

  def __getitem__(self, index):
    return self.recent_files[index]

  def count(self, item):
    return self.recent_files.count(item)

  def insert(self, index, item):
    self.recent_files.insert(index, item)
    self.save()

  def remove(self, item):
    self.recent_files.remove(item)
    self.save()

  def raw(self):
    return self.recent_files