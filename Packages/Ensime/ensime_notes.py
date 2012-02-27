import os, sys, stat, functools
import sublime, sublime_plugin
from ensime_server import EnsimeOnly
import ensime_environment
import sexp

ensime_env = ensime_environment.ensime_env

class LangNote:

  def __init__(self, lang, msg, fname, severity, start, end, line, col):
    self.lang = lang
    self.message = msg
    self.file_name = fname
    self.severity = severity
    self.start = start
    self.end = end
    self.line = line
    self.col = col

def lang_note(lang, m):
  return LangNote(
    lang, 
    m[":msg"],
    m[":file"],
    m[":severity"],
    m[":beg"],
    m[":end"],
    m[":line"],
    m[":col"])

def erase_error_highlights(view):
  view.erase_regions("ensime-error")
  view.erase_regions("ensime-error-underline")
  
def highlight_errors(view, notes):
  if notes is None:
    print "There were no notes?"
    return
  print "higlighting errors"
  errors = [view.full_line(note.start) for note in notes]
  underlines = []
  for note in notes:
    underlines += [sublime.Region(int(pos)) for pos in range(note.start, note.end)]
  view.add_regions(
    "ensime-error-underline",
    underlines,
    "invalid.illegal",
    sublime.DRAW_EMPTY_AS_OVERWRITE)
  view.add_regions(
    "ensime-error", 
    errors, 
    "invalid.illegal", 
    "cross",
    sublime.DRAW_OUTLINED)

view_notes = {}

class EnsimeNotes(sublime_plugin.TextCommand, EnsimeOnly):

  def run(self, edit, action = "add", lang = "scala", value=None):

    if not hasattr(self, "notes"):
      self.notes = []

    if action == "add":
      new_notes = [lang_note(lang, m) for m in value]
      self.notes.extend(new_notes)
      highlight_errors(self.view, self.notes)

    elif action == "clear":
      self.notes = []
      erase_error_highlights(self.view)

    elif action == "display":
      nn = self.notes
      vw = self.view
      vpos = vw.line(vw.sel()[0].begin()).begin()
      if len(nn) > 0 and len([a for a in nn if self.view.line(int(a.start)).begin() == vpos]) > 0:
        msgs = [note.message for note in self.notes]
        self.view.set_status("ensime-typer", "; ".join(set(msgs)))
      else:
        self.view.erase_status("ensime-typer")
        #sublime.set_timeout(functools.partial(self.view.run_command, "ensime_inspect_type_at_point", self.view.id()), 200)

def run_check(view):
    view.checked = True
    view.run_command("ensime_type_check_file")

class BackgroundTypeChecker(sublime_plugin.EventListener):


  def _is_valid_file(self, view):
    return bool(not view.file_name() is None and view.file_name().endswith(("scala","java")))

  def on_load(self, view):
    if self._is_valid_file(view):
      run_check(view)

  def on_post_save(self, view):
    if self._is_valid_file(view):
      run_check(view)

  def on_selection_modified(self, view):
    if self._is_valid_file(view):
      view.run_command("ensime_notes", { "action": "display" })



class EnsimeInspectTypeAtPoint(sublime_plugin.TextCommand, EnsimeOnly):

  def handle_reply(self, data):
    d = data[1][1]
    if d[1] != "<notype>":
      self.view.set_status("ensime-typer", "(" + str(d[7]) + ") " + d[5])
    else:
      self.view.erase_status("ensime-typer")

  def run(self, edit):
    if self.view.file_name():
      cl = ensime_environment.ensime_env.client()
      if not cl is None:
        cl.inspect_type_at_point(self.view.file_name(), self.view.sel()[0].begin(), self.handle_reply)



