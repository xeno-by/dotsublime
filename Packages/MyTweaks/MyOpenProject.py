import sublime, sublime_plugin
import os

class MyOpenProjectCommand(sublime_plugin.ApplicationCommand):
  def run(self):
    project_file_name, action = open(os.path.expandvars("$HOME/.sublime_scratchpad"), "r").read().splitlines()
    project_window = next(filter(lambda w: w.project_file_name() == project_file_name, sublime.windows()), None)
    if action == "OPEN?":
      status = "YEP" if project_window else "NOPE"
      with open(os.path.expandvars("$HOME/.sublime_scratchpad"), "w") as f: f.write(status)
    elif action == "FOCUS!":
      if project_window and sublime.active_window().id() != project_window.id():
        project_window.focus_group(project_window.active_group())
    else:
      print("unknown action: " + str(action))
