import sublime, sublime_plugin
import subprocess
from _winreg import *

class MykeCommand(sublime_plugin.WindowCommand):
  def run(self, cmd = "compile"):
    view = self.window.active_view()

    # how do I detect currently open project?!
    project_root = (view.settings().get("myke_project_root") if view else None) or self.window.folders()[0]
    current_file = (view.settings().get("myke_current_file") or view.file_name() if view else None) or project_root
    if view and view.settings().get("repl_external_id") == "myke_console":
      contents = view.substr(sublime.Region(0, view.size()))
      last_line = view.substr(view.lines(sublime.Region(0, view.size()))[-1])[0:-1]
      current_file = last_line

    if cmd == "log" or cmd == "commit":
      incantation = "myke " + cmd
      print("Running " + incantation)
      subprocess.Popen(incantation, shell = True)
    elif cmd == "clean":
      incantation = "myke clean \"" + current_file + "\""
      print("Running " + incantation)
      subprocess.Popen(incantation, shell = True)
    elif cmd == "console":
      if (self.window.active_view() and self.window.active_view().settings().get("repl_external_id") == "myke_console"):
        self.window.run_command("next_view_in_stack")
      else:
        found = False
        for view in self.window.views():
          if view.settings().get("repl_external_id") == "myke_console":
            found = True
            self.window.focus_view(view)
        if not found:
          self.window.run_command("repl_open", {"type": "subprocess", "encoding": "utf8", "cmd": ["myke.exe", "console"], "cwd": "$project_path", "external_id": "myke_console", "syntax": "Packages/Text/Plain Text.tmLanguage"})
    elif cmd == "repl":
      self.window.run_command("repl_open", {"type": "subprocess", "encoding": "utf8", "cmd": ["myke.exe", "repl"], "cwd": "$project_path", "external_id": "myke_repl", "syntax": "Packages/Scala/Scala.tmLanguage"})
    else:
      view_name = "myke " + cmd
      wannabes = filter(lambda v: v.name() == view_name, self.window.views())
      wannabe = wannabes[0] if len(wannabes) else self.window.new_file()
      wannabe.set_name(view_name)
      wannabe.settings().set("myke_project_root", project_root)
      wannabe.settings().set("myke_current_file", current_file)
      self.window.run_command("exec", {"title": "myke " + cmd, "cmd": ["myke", cmd, current_file], "cont": "myke_continuation", "shell": "true", "working_dir": project_root, "file_regex": "weird value stubs", "line_regex": "are necessary for sublime"})

class MykeContinuationCommand(sublime_plugin.TextCommand):
  def run(self, edit):
    view = self.view
    window = self.view.window()
    env = self.get_env()

    cont = env["Continuation"] if "Continuation" in env else None
    if cont:
      cont = env["Continuation"]
      window.run_command("exec", {"title": view.name(), "cmd": [cont], "cont": "myke_continuation", "shell": "true"})
      return

    meaningful = env["Meaningful"] == "1" if "Meaningful" in env else None
    if not meaningful:
      window.run_command("close_file")

    result_file_regex = env["ResultFileRegex"] if "ResultFileRegex" in env else ""
    result_line_regex = env["ResultLineRegex"] if "ResultLineRegex" in env else ""
    working_dir = env["WorkingDir"]
    if result_file_regex or result_line_regex:
      view.settings().set("result_file_regex", result_file_regex)
      view.settings().set("result_line_regex", result_line_regex)
      print(env["WorkingDir"])
      view.settings().set("result_base_dir", env["WorkingDir"])
      window.focus_view(view)

    view.settings().erase("no_history")
    pt = view.text_point(1, 1)
    view.sel().clear()
    view.sel().add(sublime.Region(pt))
    view.show(pt)

    message = "Myke %s upon %s" % (env["Action"], env["Target"])
    args = env["Args"] if "Args" in env else None
    if args: message = "%s with args %s" % (message, args)
    message = "%s has completed with code %s" % (message, env["Status"])
    MykeStatusMessageDisplay(window.active_view(), message)

  def get_env(self):
    hkcu = ConnectRegistry(None, HKEY_CURRENT_USER)
    key = OpenKey(hkcu, r"Software\Far2\KeyMacros\Vars", 0, KEY_ALL_ACCESS)
    env = {}
    for i in range(1024):
      try:
        name, value, t = EnumValue(key, i)
      except EnvironmentError:
        break
      if name.startswith("%%Myke"):
        env[name[6:]] = value
    CloseKey(key)
    CloseKey(hkcu)
    print("env is: " + str(env))
    return env

class MykeStatusMessageListener(sublime_plugin.EventListener):
  def on_deactivated(self, view):
    self.disable_status_message(view)

  def on_selection_modified(self, view):
    self.disable_status_message(view)

  def disable_status_message(self, view):
    view.settings().set("myke_status_message", None)

class MykeStatusMessageDisplay():
  def __init__(self, view, message):
    view.settings().set("myke_status_message", message)
    sublime.set_timeout(lambda: self.run(view), 1000)

  def run(self, view):
    message = view.settings().get("myke_status_message")
    if message:
      sublime.status_message(message)
      sublime.set_timeout(lambda: self.run(view), 1000)
