import sublime, sublime_plugin
import time
from functools import partial as bind

# sure thing, it's a hack, but I have no idea how to get hold of a view created by clone_file
shared = {}
class CloneDaemon(sublime_plugin.EventListener):
  def on_clone_async(self, view):
    proto = shared["proto"]
    shared["proto"] = None
    if proto:
      window = view.window()
      group, index = window.get_view_index(proto)
      if group != 1: window.set_view_index(view, 1, len(window.views_in_group(1)))
      view.show(proto.visible_region())
      view.set_viewport_position(proto.viewport_position())
      view.sel().clear()
      for sel in proto.sel():
        view.sel().add(sel)

class CloneFileAndSplit(sublime_plugin.WindowCommand):
  def run(self):
    window = self.window
    view = window.active_view()
    shared["proto"] = view
    window.run_command("clone_file")
    window.run_command("set_layout", {"cols": [0.0, 0.5, 1.0], "rows": [0.0, 1.0], "cells": [[0, 0, 1, 1], [1, 0, 2, 1]]})
    view.settings().set("myclone", True)

class UndoCloneFileAndSplit(sublime_plugin.WindowCommand):
  def run(self):
    self.window.active_view().settings().set("myclone", False)
    self.window.run_command("close_file")
    if len(self.window.views_in_group(1)) == 0:
      self.window.run_command("set_layout", {"cols": [0.0, 1.0], "rows": [0.0, 1.0], "cells": [[0, 0, 1, 1]]})

class MoveFileToSplit(sublime_plugin.WindowCommand):
  def run(self):
    window = self.window
    view = window.active_view()
    layout = window.get_layout()
    if len(layout["rows"]) == 2 and len(layout["cols"]) == 2:
      window.run_command("set_layout", {"cols": [0.0, 0.5, 1.0], "rows": [0.0, 1.0], "cells": [[0, 0, 1, 1], [1, 0, 2, 1]]})
      window.focus_view(view)
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
    curr = self.window.active_group()
    self.window.run_command("split_pane", {"create_pane_in_direction": "right"})
    if self.window.active_group() != curr:
      self.window.run_command("split_pane", {"destroy_pane_in_direction": "left"})
    self.window.run_command("split_pane", {"create_pane_in_direction": "left"})
    if self.window.active_group() != curr:
      self.window.run_command("split_pane", {"destroy_pane_in_direction": "right"})
    self.window.run_command("split_pane", {"create_pane_in_direction": "up"})
    if self.window.active_group() != curr:
      self.window.run_command("split_pane", {"destroy_pane_in_direction": "down"})
    self.window.run_command("split_pane", {"create_pane_in_direction": "down"})
    if self.window.active_group() != curr:
      self.window.run_command("split_pane", {"destroy_pane_in_direction": "up"})

class MySplitHorizontal(sublime_plugin.WindowCommand):
  def run(self):
    self.window.run_command("split_pane", {"create_pane_in_direction": "right"})
    self.window.run_command("split_pane", {"travel_to_pane_in_direction": "right"})

class MySplitVertical(sublime_plugin.WindowCommand):
  def run(self):
    self.window.run_command("split_pane", {"create_pane_in_direction": "down"})
    self.window.run_command("split_pane", {"travel_to_pane_in_direction": "down"})

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
