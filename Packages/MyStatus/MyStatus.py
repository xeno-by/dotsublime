import sublime, sublime_plugin

class CharacterPosition(sublime_plugin.EventListener):
  def on_activated(self, view):
    self.update_status(view)

  def on_selection_modified(self, view):
    self.update_status(view)

  def update_status(self, view):
    row, col = view.rowcol(view.size())
    view.set_status("zzMyStatus", "Lines %d, Character %d" % (row + 1, view.sel()[0].a + 1))
