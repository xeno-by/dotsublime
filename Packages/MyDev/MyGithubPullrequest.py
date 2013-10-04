import sublime, sublime_plugin
import os
from subprocess import Popen, call, PIPE

class MyGithubPullrequest(sublime_plugin.TextCommand):
  def run(self, edit):
    self.w = self.view.window()
    self.v = self.view

    file_name = self.v.file_name() if self.v.file_name() else self.detect_project_root()
    full_name = os.path.realpath(file_name)
    folder_name, _ = os.path.split(full_name)

    shell = Popen([os.environ["SHELL"], "-c", "pullrequest"], cwd = folder_name, stdout=PIPE)
    output = shell.communicate()[0].decode()[:-1]
    if output:
      output = output[:1].upper() + output[1:]
      sublime.status_message(output)
      call(["growlnotify", "-n", "Pull Request", "-m", output])

  # TODO: copy/pasted from MyGaika.py. how do I remove duplication?
  def detect_project_root(self):
    def try_project_root(path):
      if path:
        if "sandbox" in path:
          return os.path.abspath(path + "/..")
        if os.path.exists(os.path.join(path, "sandbox")):
          return path
        if os.path.exists(os.path.join(path, "project")):
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
    except:
      pass
