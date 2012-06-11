import sublime
from sublime_plugin import EventListener
from ensime_common import *

class EnsimeHighlights(EnsimeCommon):
  def hide(self):
    self.v.erase_regions("ensime-error")
    self.v.erase_regions("ensime-error-underline")

  def show(self):
    # filter notes against self.f
    # don't forget to use os.realpath to defeat symlinks
    errors = [self.v.full_line(note.start) for note in self.env.notes]
    underlines = []
    for note in self.env.notes:
      underlines += [sublime.Region(int(pos)) for pos in range(note.start, note.end)]
    if self.env.settings.get("error_highlight") and self.env.settings.get("error_underline"):
      self.v.add_regions(
        "ensime-error-underline",
        underlines,
        "invalid.illegal",
        sublime.DRAW_EMPTY_AS_OVERWRITE)
    if self.env.settings.get("error_highlight"):
      self.v.add_regions(
        "ensime-error",
        errors,
        "invalid.illegal",
        self.env.settings.get("error_icon"),
        sublime.DRAW_OUTLINED)

  def refresh(self):
    if self.env.settings.get("error_highlight"):
      self.show()
    else:
      self.hide()

class EnsimeHighlightCommand(ConnectedEnsimeOnly, EnsimeWindowCommand):
  def is_enabled(self, enable = True):
    now = not not self.env.settings.get("error_highlight")
    wannabe = not not enable
    return super(type(self).__mro__[0], self).is_enabled() and now != wannabe

  def run(self, enable = True):
    self.env.settings.set("error_highlight", not not enable)
    sublime.save_settings("Ensime.sublime-settings")
    EnsimeHighlights(self.v).hide()
    if enable:
      self.type_check_file(self.f)

class EnsimeHighlightDaemon(EventListener):
  def with_api(self, view, what):
    api = ensime_api(view)
    connected = hasattr(api, "controller") and api.controller and api.controller.connected
    if connected and api.in_project(view.file_name()):
      what(api)

  def on_load(self, view):
    self.with_api(view, lambda api: api.type_check_file(view.file_name()))

  def on_post_save(self, view):
    self.with_api(view, lambda api: api.type_check_file(view.file_name()))

  def on_activate(self, view):
    self.with_api(view, lambda api: EnsimeHighlights(view).refresh())

  def on_selection_modified(self, view):
    self.with_api(view, self.display_errors_in_statusbar)

  def display_errors_in_statusbar(self, api):
    bol = api.v.line(api.v.sel()[0].begin()).begin()
    eol = api.v.line(api.v.sel()[0].begin()).end()
    # filter notes against self.f
    # don't forget to use os.realpath to defeat symlinks
    msgs = [note.message for note in api.notes if (bol <= note.start and note.start <= eol) or (bol <= note.end and note.end <= eol)]
    if msgs:
      api.v.set_status("ensime-typer", "; ".join(msgs))
    else:
      api.v.erase_status("ensime-typer")
