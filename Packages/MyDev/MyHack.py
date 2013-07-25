import sublime, sublime_plugin
import os, re, shutil
from functools import partial as bind
from subprocess import Popen, PIPE

class MyHackCommand(sublime_plugin.ApplicationCommand):
  def run(self):
    command, project_file_name, action = open(os.path.expandvars("$HOME/.hack_sublime"), "r").read().splitlines()
    add, delete = command.startswith("+"), command.startswith("-")
    if action == "OPEN?":
      for window in sublime.windows():
        if window.project_file_name() == project_file_name:
          with open(os.path.expandvars("$HOME/.hack_sublime"), "w") as f: f.write("YEP")
          return
      with open(os.path.expandvars("$HOME/.hack_sublime"), "w") as f: f.write("NOPE")
    elif action == "FOCUS!":
      pass
    else:
      print("unknown action: " + str(action))
