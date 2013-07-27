import sublime, sublime_plugin
import os, re, shutil
from functools import partial as bind
from subprocess import Popen, PIPE

class MyHackCommand(sublime_plugin.ApplicationCommand):
  def run(self):
    command, project_file_name, action = open(os.path.expandvars("$HOME/.hack_sublime"), "r").read().splitlines()
    add, delete = command.startswith("+"), command.startswith("-")
    project_window = next(filter(lambda w: w.project_file_name() == project_file_name, sublime.windows()), None)
    if action == "OPEN?":
      status = "YEP" if project_window else "NOPE"
      with open(os.path.expandvars("$HOME/.hack_sublime"), "w") as f: f.write(status)
    elif action == "FOCUS!":
      if project_window and sublime.active_window().id() != project_window.id():
        project_window.focus_group(project_window.active_group())
    else:
      print("unknown action: " + str(action))
