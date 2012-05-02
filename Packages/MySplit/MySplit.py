import sublime, sublime_plugin

class MySplitHorizontally(sublime_plugin.WindowCommand):
  def run(self):
    window = self.window
    view = window.active_view()
    window.run_command("set_layout", {"cols": [0.0, 0.5, 1.0], "rows": [0.0, 1.0], "cells": [[0, 0, 1, 1], [1, 0, 2, 1]]})
    window.set_view_index(view, 1, len(window.views_in_group(1)))

class MySplitVertically(sublime_plugin.WindowCommand):
  def run(self):
    window = self.window
    view = window.active_view()
    window.run_command("set_layout", {"cols": [0.0, 1.0], "rows": [0.0, 0.5, 1.0], "cells": [[0, 0, 1, 1], [0, 1, 1, 2]]})
    window.set_view_index(view, 1, len(window.views_in_group(1)))

class MyUnsplit(sublime_plugin.WindowCommand):
  def run(self):
    window = self.window
    view = window.active_view()
    window.run_command("set_layout", {"cols": [0.0, 1.0], "rows": [0.0, 1.0], "cells": [[0, 0, 1, 1]]})
    window.focus_view(view)

class CloneFileAndSplit(sublime_plugin.WindowCommand):
  def run(self):
    window = self.window
    view = window.active_view()
    window.run_command("clone_file")
    window.run_command("set_layout", {"cols": [0.0, 0.5, 1.0], "rows": [0.0, 1.0], "cells": [[0, 0, 1, 1], [1, 0, 2, 1]]})
    window.set_view_index(view, 1, len(window.views_in_group(1)))
