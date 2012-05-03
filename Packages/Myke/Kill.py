import sublime, sublime_plugin
import subprocess
import os

class MykeKill(sublime_plugin.WindowCommand):
  def run(self):
    window = self.window
    view = window.active_view()

    is_console = False
    if (view and view.settings().get("repl_external_id") == "myke_console"):
      is_console = True

    window.run_command("exec", {"kill": True })
    view.run_command("repl_kill")

    if is_console:
      # window.focus_view(view)
      # view.settings().set("repl_external_id", "")
      # window.run_command("clone_file")
      # window.focus_view(view)
      # window.run_command("close_file")
      window.run_command("repl_open", {"type": "subprocess", "encoding": "utf8", "cmd": ["myke.exe", "/S", "console"], "cwd": """C:\Projects\Perf_Bad""", "external_id": "myke_console", "view_id": view.id(), "syntax": "Packages/Text/Plain Text.tmLanguage"})

class MykeCtrlC(sublime_plugin.WindowCommand):
  def run(self):
    window = self.window
    view = window.active_view()
    sel = view.sel()

    if len(sel) == 1 and sel[0].a == sel[0].b:
      window.run_command("myke_kill")
    else:
      window.run_command("copy")