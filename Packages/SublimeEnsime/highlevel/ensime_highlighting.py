class EnsimeHighlights(EnsimeCommon):
  def hide(self):
    self.v.erase_regions("ensime-error")
    self.v.erase_regions("ensime-error-underline")

  def show(self):
    # filter notes against self.f
    # don't forget to use os.realpath to defeat symlinks
    errors = [self.v.full_line(note.start) for note in self.notes]
    underlines = []
    for note in self.notes:
      underlines += [sublime.Region(int(pos)) for pos in range(note.start, note.end)]
    if self.settings.get("error_highlight") and self.settings.get("error_underline"):
      self.v.add_regions(
        "ensime-error-underline",
        underlines,
        "invalid.illegal",
        sublime.DRAW_EMPTY_AS_OVERWRITE)
    if self.settings.get("error_highlight"):
      self.v.add_regions(
        "ensime-error",
        errors,
        "invalid.illegal",
        self.settings.get("error_icon"),
        sublime.DRAW_OUTLINED)

  def refresh(self):
    if self.settings.get("error_highlight"):
      self.show()
    else:
      self.hide()

class EnsimeHighlightCommand(EnsimeWindowCommand):
  def is_enabled(self, enable = True):
    now = not not self.settings.get("error_highlight")
    wannabe = not not enable
    running = ConnectedEnsimeOnly.is_enabled(self)
    return running and now != wannabe

  def run(self, enable = True):
    self.settings.set("error_highlight", not not enable)
    sublime.save_settings("Ensime.sublime-settings")
    EnsimeHighlights(self.v).hide()
    if enable:
      self.type_check_file(self.f)

class EnsimeHighlightDaemon(sublime_plugin.EventListener):
  def on_load(self, view):
    api = EnsimeApi(view)
    if api and api.in_project(view.file_name()):
      api.type_check_file(view.file_name())

  def on_post_save(self, view):
    api = EnsimeApi(view)
    if api and api.in_project(view.file_name()):
      api.type_check_file(view.file_name())

  def on_activate(self, view):
    api = EnsimeApi(view)
    if api and api.in_project(view.file_name()):
      EnsimeHighlights(view).refresh()

  def on_selection_modified(self, view):
    api = EnsimeApi(view)
    if api and api.in_project(view.file_name()):
      bol = view.line(view.sel()[0].begin()).begin()
      eol = view.line(view.sel()[0].begin()).end()
      msgs = [note.message for note in self.notes if (bol <= note.start and note.start <= eol) or (bol <= note.end and note.end <= eol)]
      if msgs:
        self.view.set_status("ensime-typer", "; ".join(msgs))
      else:
        self.view.erase_status("ensime-typer")
