import sublime, sublime_plugin
import os, re, shutil
from functools import partial as bind
from subprocess import Popen, PIPE

class MyHackCommand(sublime_plugin.ApplicationCommand):
  def activate_or_deactivate_project_window(self):
    for window in sublime.windows():
      if window.folders():
        if self.home in window.folders():
          self.window = window
          if self.delete:
            window.run_command("close")
          else:
            # activate this window
            # but how???
            # anyways we're fine, since for now it's enough to just close the extraneous empty window
            pass
      else:
        if not window.views():
          window.run_command("close")

  def generate_snippets_if_necessary(self):
    if self.add:
      if self.target == "snippet":
        self.window.run_command("my_sandbox_vanilla_snippet")
      elif self.target == "macrosnippet":
        self.window.run_command("my_sandbox_macro_snippet")

  def run(self):
    with open(os.path.expandvars("$HOME/.hack_sublime"), "r") as f:
      lines = f.read().splitlines()
      self.target = lines[0]
      self.home = lines[1] + "/sandbox"
    self.add, self.delete = self.target.startswith("+"), self.target.startswith("-")
    if self.add or self.delete: self.target = self.target[1:]
    self.activate_or_deactivate_project_window()
    self.generate_snippets_if_necessary()
