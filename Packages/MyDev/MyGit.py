import sublime, sublime_plugin
import os
from subprocess import call

class MyGitCommand(sublime_plugin.WindowCommand):
  def __init__(self, window):
    sublime_plugin.WindowCommand.__init__(self, window)

  def run(self):
    self.view = self.window.active_view()
    if self.view and self.view.file_name():
      self.cwd = os.path.dirname(self.view.file_name())
      self.target = self.view.file_name()
    else:
      self.cwd = self.window.folders()[1] + "/.."
      self.target = None
    self.do_run()

  def do_run(self):
    print self.cwd
    call(["stree"], cwd = self.cwd)

class MyGitLogAll(MyGitCommand):
  def do_run(self):
    call(["gitblit", "log"], cwd = self.cwd)

class MyGitLogThis(MyGitCommand):
  def do_run(self):
    if self.target:
      call(["gitblit", "log", self.target], cwd = self.cwd)

class MyGitBlame(MyGitCommand):
  def do_run(self):
    if self.target:
      call(["gitblit", "blame", self.target], cwd = self.cwd)
