import sublime, sublime_plugin
import os

class MyTracker(sublime_plugin.EventListener):
  def on_activated_async(self, v):
    current_file = v.file_name() or ("* " + str(v.name()))
    current_folder = (list(filter(lambda folder: current_file.startswith(folder + "/"), v.window().folders())) or ["<no folder>"])[0]
    current_project = v.window().project_file_name() or "<no project>"
    latest = os.path.expandvars("$HOME/.sublime_latest")
    with open(latest, "w") as f: f.write(current_file + "\n" + current_folder + "\n" + current_project)
