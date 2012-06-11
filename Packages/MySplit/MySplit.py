import sublime, sublime_plugin

class CloneFileAndSplit(sublime_plugin.WindowCommand):
  def run(self):
    window = self.window
    view = window.active_view()
    window.run_command("clone_file")
    window.run_command("set_layout", {"cols": [0.0, 0.5, 1.0], "rows": [0.0, 1.0], "cells": [[0, 0, 1, 1], [1, 0, 2, 1]]})
    new = window.active_view()
    new.show(view.visible_region())
    new.set_viewport_position(view.viewport_position())
    for sel in view.sel():
      new.sel().add(sel)
    group, index = window.get_view_index(new)
    if group != 1:
      window.set_view_index(new, 1, len(window.views_in_group(1)))
    window.focus_view(view)
    window.focus_view(new)

class MoveFileToSplit(sublime_plugin.WindowCommand):
  def run(self):
    window = self.window
    view = window.active_view()
    layout = window.get_layout()
    if len(layout["rows"]) == 2 and len(layout["cols"]) == 2:
      window.run_command("set_layout", {"cols": [0.0, 0.5, 1.0], "rows": [0.0, 1.0], "cells": [[0, 0, 1, 1], [1, 0, 2, 1]]})
    group, index = window.get_view_index(view)
    curr = window.active_group()
    total = window.num_groups()
    curr = curr + 1
    if curr == total:
      curr = curr - total
    if group != curr:
      window.set_view_index(view, curr, len(window.views_in_group(1)))

class MyLayout1(sublime_plugin.WindowCommand):
  def run(self):
    window = self.window
    view = window.active_view()
    window.run_command("set_layout", {"cols": [0.0, 1.0], "rows": [0.0, 1.0], "cells": [[0, 0, 1, 1]]})
    if view:
      window.focus_view(view)

class MyLayout2(sublime_plugin.WindowCommand):
  def run(self):
    window = self.window
    view = window.active_view()
    window.run_command("set_layout", {"cols": [0.0, 0.5, 1.0], "rows": [0.0, 1.0], "cells": [[0, 0, 1, 1], [1, 0, 2, 1]]})
    if view:
      window.focus_view(view)

class MyLayout8(sublime_plugin.WindowCommand):
  def run(self):
    window = self.window
    view = window.active_view()
    window.run_command("set_layout", {"cols": [0.0, 1.0], "rows": [0.0, 0.5, 1.0], "cells": [[0, 0, 1, 1], [0, 1, 1, 2]]})
    if view:
      window.focus_view(view)

class MySplitUnsplit(sublime_plugin.WindowCommand):
  def run(self):
    print "MySplitUnsplit"

class MySplitHorizontal(sublime_plugin.WindowCommand):
  def run(self):
    print "MySplitHorizontal"

class MySplitVertical(sublime_plugin.WindowCommand):
  def run(self):
    print "MySplitVertical"

class MySplitNext(sublime_plugin.WindowCommand):
  def run(self):
    window = self.window
    curr = window.active_group()
    total = window.num_groups()
    curr = curr + 1
    if curr == total:
      curr = curr - total
    window.focus_group(curr)

class MySplitPrev(sublime_plugin.WindowCommand):
  def run(self):
    window = self.window
    curr = window.active_group()
    total = window.num_groups()
    curr = curr - 1
    if curr == -1:
      curr = curr + total
    window.focus_group(curr)

class MySplitMoveToNext(sublime_plugin.WindowCommand):
  def run(self):
    window = self.window
    view = window.active_view()
    curr = window.active_group()
    total = window.num_groups()
    curr = curr + 1
    if curr == total:
      curr = curr - total
    window.set_view_index(window.active_view(), curr, len(window.views_in_group(curr)))

class MySplitMoveToPrev(sublime_plugin.WindowCommand):
  def run(self):
    window = self.window
    view = window.active_view()
    curr = window.active_group()
    total = window.num_groups()
    curr = curr - 1
    if curr == -1:
      curr = curr + total
    window.set_view_index(window.active_view(), curr, len(window.views_in_group(curr)))

# http://www.sublimetext.com/forum/viewtopic.php?f=6&t=5842
# https://gist.github.com/1320281/ade9d769ea76ac5f882c8a0f0238efae13e905e9
class MySplitTest(sublime_plugin.WindowCommand):
  def run(self):
    window = self.window
    window.run_command("set_layout", {
      "cols": [0.0, 0.33, 0.5, 0.66, 1.0],
      "rows": [0.0, 0.5, 1.0],
      "cells": [
                [0, 0, 2, 1], [2, 0, 4, 1],
                [0, 1, 1, 2], [1, 1, 3, 2], [3, 1, 4, 2]]
    })

class ReLayouter(sublime_plugin.EventListener):
  def on_new(self, view):
    # print "on_new: " + (view.name() or view.file_name() or "")
    sublime.set_timeout(lambda: self.recheck_new(view), 100)

  def recheck_new(self, view):
    # print "recheck_new: " + (view.name() or view.file_name() or "")
    if self.is_special(view):
      if self.window and self.window.num_groups() > 1:
        g, i = self.window.get_view_index(view)
        if g != 1:
          self.window.set_view_index(view, 1, len(self.window.views_in_group(1)))

  def on_deactivated(self, view):
    # print "on_deactivated: " + (view.name() or view.file_name() or "")
    self.pv = view

  def on_activated(self, view):
    # print "on_activated: " + (view.name() or view.file_name() or "")
    self.cv = view
    self.window = view.window()
    if self.needs_relayout():
      print "needs relayout: " + (view.name() or view.file_name() or "")
      self.relayout()

  def is_special(self, view):
    name = view.name() or ""
    if name.startswith("myke ") or name == "Find Results":
      return True

  def needs_relayout(self):
    if hasattr(self, "pv") and hasattr(self, "cv") and self.window and self.window.num_groups() > 1:
      pg, pi = self.window.get_view_index(self.pv)
      cg, ci = self.window.get_view_index(self.cv)
      if pg == cg and self.pv != self.cv:
        pn = self.pv.name() or ""
        if pn.startswith("myke ") or pn == "Find Results":
          return True

  def relayout(self):
    # crashes!! very weird
    # pg, pi = self.window.get_view_index(self.pv)
    # if pg != 1:
    #   self.window.set_view_index(self.pv, 1, len(self.window.views_in_group(1)))
    cg, ci = self.window.get_view_index(self.cv)
    if cg != 0 and not self.is_special(self.cv):
      self.window.set_view_index(self.cv, 0, len(self.window.views_in_group(0)))
    self.window.focus_view(self.cv)
