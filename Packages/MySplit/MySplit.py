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
    window.set_view_index(new, 1, len(window.views_in_group(1)))

class MyLayout1(sublime_plugin.WindowCommand):
  def run(self):
    window = self.window
    view = window.active_view()
    window.run_command("set_layout", {"cols": [0.0, 1.0], "rows": [0.0, 1.0], "cells": [[0, 0, 1, 1]]})
    window.focus_view(view)

class MyLayout2(sublime_plugin.WindowCommand):
  def run(self):
    window = self.window
    view = window.active_view()
    window.run_command("set_layout", {"cols": [0.0, 0.5, 1.0], "rows": [0.0, 1.0], "cells": [[0, 0, 1, 1], [1, 0, 2, 1]]})
    window.focus_view(view)

class MyLayout8(sublime_plugin.WindowCommand):
  def run(self):
    window = self.window
    view = window.active_view()
    window.run_command("set_layout", {"cols": [0.0, 1.0], "rows": [0.0, 0.5, 1.0], "cells": [[0, 0, 1, 1], [0, 1, 1, 2]]})
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
    window.set_view_index(window.active_view(), curr, len(window.views_in_group(1)))

class MySplitMoveToPrev(sublime_plugin.WindowCommand):
  def run(self):
    window = self.window
    view = window.active_view()
    curr = window.active_group()
    total = window.num_groups()
    curr = curr - 1
    if curr == -1:
      curr = curr + total
    window.set_view_index(window.active_view(), curr, len(window.views_in_group(1)))

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
