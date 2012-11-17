import sublime, sublime_plugin
import os
from subprocess import Popen, call, PIPE

class MyGithubPullrequest(sublime_plugin.TextCommand):
  def run(self, edit):
    if not self.view.file_name(): return
    full_name = os.path.realpath(self.view.file_name())
    folder_name, _ = os.path.split(full_name)

    shell = Popen([os.environ["SHELL"], "-c", "pullrequest"], cwd = folder_name, stdout=PIPE)
    output = shell.communicate()[0][:-1]
    if output:
      output = output[:1].upper() + output[1:]
      sublime.status_message(output)
      call(["growlnotify", "-n", "Pull Request", "-m", output])
