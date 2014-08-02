import sublime, sublime_plugin
import subprocess, os, time, re, json

class GaikaCommand(sublime_plugin.WindowCommand):
  def run(self, cmd, args=[]):
    self.w = self.window
    self.v = self.w.active_view()
    self.cmd = cmd
    self.args = args or []
    self.current_file = self.detect_current_file()
    self.project_root = self.detect_project_root()
    self.launch_gaika()

  def detect_current_file(self):
    current_file = self.v.file_name() if self.v else None
    if current_file and current_file.endswith(".src"): self.args.append(current_file)
    if current_file and current_file.endswith(".tex"): self.args.append(current_file)
    if current_file and current_file.endswith(".sty"): self.args.append(current_file)
    if current_file and current_file.endswith(".bib"): self.args.append(current_file)
    if current_file and current_file.endswith(".c"): self.args.append(current_file)
    return current_file

  def detect_project_root(self):
    def try_project_root(path):
      if path:
        if "sandbox" in path:
          return os.path.abspath(path + "/..")
        if os.path.exists(os.path.join(path, "sandbox")):
          return path
        if os.path.exists(os.path.join(path, "project")):
          return path
        if os.path.exists(os.path.join(path, "Makefile")):
          return path
        if os.path.exists(os.path.join(path, "pom.xml")):
          return path
        parent = os.path.dirname(path)
        if parent != path:
          return try_project_root(parent)

    try:
      maybe_root = try_project_root(self.current_file)
      if maybe_root: return maybe_root

      project = self.w.project_file_name()
      folders = json.load(open(project))["folders"]
      for folder in folders:
        maybe_root = try_project_root(folder["path"])
        if maybe_root: return maybe_root

      return folders[0]["path"]
    except:
      pass

  def launch_gaika(self):
    existing_id = None
    for view in self.w.views():
      if view.name() == "*REPL* [gaika compile]":
        existing_id = view.id()

    # repl_settings = sublime.load_settings("SublimeREPL.sublime-settings")
    # rv_settings = repl_settings.get("repl_view_settings", {})
    # rv_settings["open_repl_in_group"] = 1
    # repl_settings.set("repl_view_settings", rv_settings)
    # sublime.save_settings("SublimeREPL.sublime-settings")

    cmd = ["gaika", self.cmd] + self.args
    self.w.run_command("repl_open", {
      "type": "subprocess",
      "encoding": "utf8",
      "external_id": " ".join(cmd[0:2]),
      "view_id": existing_id,
      "cmd": cmd,
      "cwd": self.project_root
    })
