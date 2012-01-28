import sublime, sublime_plugin

class WordCount(sublime_plugin.EventListener):
  def on_activated(self, view):
    self.update_status(view)

  def on_selection_modified(self, view):
    self.update_status(view)

  def update_status(self, view):
    view.set_status("Character", "Character %d" % (view.sel()[0].a + 1))
