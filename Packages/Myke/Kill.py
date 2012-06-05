import sublime, sublime_plugin
import subprocess
import os

class MykeKill(sublime_plugin.WindowCommand):
  def run(self):
    window = self.window
    view = window.active_view()
    view_id = view.id() if view else None
    is_console = view and view.settings().get("repl_external_id") == "myke_console"

    window.run_command("exec", {"kill": True })
    if view:
      view.run_command("repl_kill")

    if is_console:
      # todo. automatically figure out the cwd from console output
      cwd = view.settings().get("cwd")
      window.run_command("repl_open", {"type": "subprocess", "encoding": "utf8", "cmd": ["myke.exe", "/S", "console"], "cwd": cwd, "view_id": view_id, "external_id": "myke_console", "syntax": "Packages/Text/Plain Text.tmLanguage"})
