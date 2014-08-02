import sublime, sublime_plugin
import os

class MyTracker(sublime_plugin.EventListener):
  def on_activated_async(self, v):
    basedir = v.settings().get("result_base_dir")
    w = v.window()
    folders = w.folders() if w else []
    current_file = (v.file_name() or ("* " + str(v.name()))) if not basedir else os.path.join(basedir, "dummy.path")
    current_folder = ((list(filter(lambda folder: current_file.startswith(folder + "/"), folders)) or ["<no folder>"])[0]) if not basedir else basedir
    current_project = (w.project_file_name() if w else None) or "<no project>"
    latest = os.path.expandvars("$HOME/.sublime_latest")
    with open(latest, "w") as f: f.write(current_file + "\n" + current_folder + "\n" + current_project)
