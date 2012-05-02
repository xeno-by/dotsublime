import sublime, sublime_plugin
import subprocess
import os

class MykeKill(sublime_plugin.WindowCommand):
  def run(self):
    self.window.run_command("exec", {"kill": True })
    self.window.active_view().run_command("repl_kill")
