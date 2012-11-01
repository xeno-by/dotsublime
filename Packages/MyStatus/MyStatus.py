# Partially taken from https://github.com/SublimeText/SideBarGit/blob/master/StatusBarBranch.py

import sublime, sublime_plugin
import threading, time, subprocess, os
from functools import partial as bind

class MyGitBranchListener(sublime_plugin.EventListener):
  def __init__(self):
    self.last_update = 0

  def on_load(self, v):
    self.update_status(v)

  def on_activated(self, v):
    self.update_status(v)

  def update_status(self, v):
    if v and v.file_name() and v.window() and v.window().active_view() and v.window().active_view().id() == v.id():
      threshold_ms = 2000
      if time.time() - self.last_update > threshold_ms / 1000:
        self.last_update = time.time()
        MyGitBranchGetter(v.file_name(), v).start()
      else:
        sublime.set_timeout(bind(self.update_status, v), threshold_ms)

class MyGitBranchGetter(threading.Thread):
  def __init__(self, f, v):
    threading.Thread.__init__(self)
    self.f = f
    self.v = v

  def run(self):
    process = subprocess.Popen(["git", "rev-parse", "--abbrev-ref", "HEAD"], stdout = subprocess.PIPE, cwd = os.path.dirname(self.f))
    current_branch = process.communicate()[0].strip()
    sublime.set_timeout(lambda: self.v.set_status("aaa_git_branch", current_branch), 0)

class MyCharacterPositionListener(sublime_plugin.EventListener):
  def on_activated(self, view):
    self.update_status(view)

  def on_selection_modified(self, view):
    self.update_status(view)

  def update_status(self, view):
    row, col = view.rowcol(view.size())
    curr_char = str(view.sel()[0].a + 1) if len(view.sel()) == 1 else "n/a"
    view.set_status("zzMyStatus", "Lines %d, Character %s" % (row + 1, curr_char))
