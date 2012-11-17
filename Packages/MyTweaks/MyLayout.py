import sublime, sublime_plugin
import time, functools
from functools import partial as bind

class LayoutDaemon(sublime_plugin.EventListener):
  def __init__(self):
    self.last_selection_modified = 0
    self.last_view_count = -1000

  def on_new(self, view):
    # print "on_new: " + (view.name() or view.file_name() or "")
    prev = sublime.active_window().active_view()
    sublime.set_timeout(lambda: self.recheck_new(view, prev), 100)

  def recheck_new(self, view, prev):
    # print "recheck_new: " + (view.name() or view.file_name() or "")
    if self.is_special(view):
      if self.window and self.window.num_groups() > 1:
        g, i = self.window.get_view_index(view)
        if g != 1:
          self.window.set_view_index(view, 1, len(self.window.views_in_group(1)))
          self.window.focus_view(prev)
          self.window.focus_view(view)

  def on_deactivated(self, view):
    # print "on_deactivated: " + (view.name() or view.file_name() or "")
    self.pv = view

  def on_activated(self, view):
    # print "on_activated: " + (view.name() or view.file_name() or "")

    # works around Sublime's bug that makes it always activate the last view group on startup
    # regardless of what group was actually active on shutdown
    if view.window():
      if view.name() or view.file_name():
        if not hasattr(self, "active_group"):
          group_to_activate = sublime.load_settings("MyLayout.sublime-settings").get("active_group", 0)
          self.active_group = group_to_activate
          self.init_time = time.time()
          view.window().focus_group(group_to_activate)
      if hasattr(self, "active_group"):
        if self.active_group != view.window().active_group():
          delta = time.time() - self.init_time
          if delta > 0.2:
            self.active_group = view.window().active_group()
            settings = sublime.load_settings("MyLayout.sublime-settings")
            settings.set("active_group", self.active_group)
            sublime.save_settings("MyLayout.sublime-settings")
          else:
            view.window().focus_group(self.active_group)

    self.cv = view
    self.window = view.window()
    if self.needs_relayout():
      # print "needs relayout: " + (view.name() or view.file_name() or "")
      self.relayout()

  def is_special(self, view):
    name = view.name() or ""
    if name.startswith("gaika ") or name == "Find Results" or name == "Ensime notes" or name == "Ensime output" or name == "Ensime stack" or name == "Ensime locals":
      return True

  def needs_relayout(self):
    if hasattr(self, "pv") and hasattr(self, "cv") and self.window and self.window.num_groups() > 1:
      pg, pi = self.window.get_view_index(self.pv)
      cg, ci = self.window.get_view_index(self.cv)
      if pg == cg and self.pv != self.cv:
        if self.is_special(self.pv):
          # relayout only if we jump into a new view by the means of double-clicking
          # if we navigate normally, there's no need in relayouting
          delta_t = time.time() - self.last_selection_modified
          delta_n = len(self.window.views()) - self.last_view_count
          return delta_t < 0.2 and delta_n != 0

  def on_selection_modified(self, view):
    if view.window():
      self.last_view_count = len(view.window().views())
    self.last_selection_modified = time.time()

  def relayout(self):
    # crashes!! very weird
    # pg, pi = self.window.get_view_index(self.pv)
    # if pg != 1:
    #   self.window.set_view_index(self.pv, 1, len(self.window.views_in_group(1)))
    cg, ci = self.window.get_view_index(self.cv)
    if cg != 0 and not self.is_special(self.cv):
      self.window.set_view_index(self.cv, 0, len(self.window.views_in_group(0)))
    self.window.focus_view(self.cv)
