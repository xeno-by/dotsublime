import sublime, sublime_plugin

class CharacterPosition(sublime_plugin.EventListener):
  def on_activated(self, view):
    self.update_status(view)

  def on_selection_modified(self, view):
    self.update_status(view)

  def update_status(self, view):
    row, col = view.rowcol(view.size())
    curr_char = str(view.sel()[0].a + 1) if len(view.sel()) == 1 else "n/a"
    view.set_status("zzMyStatus", "Lines %d, Character %s" % (row + 1, curr_char))
