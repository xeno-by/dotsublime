import sublime, sublime_plugin
import subprocess
import os
from _winreg import *

class MykeCommand(sublime_plugin.WindowCommand):
  def run(self, cmd = "compile", args=""):
    self.cmd = cmd
    self.args = args or ""

    # how do I reliably detect currently open project?!
    view = self.window.active_view()
    self.project_root = (view.settings().get("myke_project_root") if view else None) or self.window.folders()[0]
    self.current_file = (view.settings().get("myke_current_file") or view.file_name() if view else None) or project_root
    self.current_dir = view.settings().get("myke_current_file") or view.file_name() if view else None
    self.current_dir = os.path.dirname(self.current_dir) if self.current_dir else self.project_root
    if view and view.settings().get("repl_external_id") == "myke_console":
      contents = view.substr(sublime.Region(0, view.size()))
      last_line = view.substr(view.lines(sublime.Region(0, view.size()))[-1])[0:-1]
      self.current_file = last_line

    myke_require_prefix = view.settings().get("myke_require_prefix") if view else None
    view.settings().set("myke_require_prefix", False)
    if myke_require_prefix:
      self.window.show_input_panel("Command prefix:", "", self.prefix_input, None, None)
    else:
      self.launch_myke()

  def prefix_input(self, prefix):
    view = self.window.active_view()
    self.args = self.args if not self.args else self.args + " "
    self.args = self.args + str(prefix)
    self.launch_myke()

  def launch_myke(self):
    if self.cmd == "log" or self.cmd == "commit":
      incantation = "myke /S " + self.cmd + " " + self.args
      print("Running " + incantation)
      subprocess.Popen(incantation, shell = True, cwd = self.current_dir)
    elif self.cmd == "blame":
      incantation = "myke /S " + self.cmd + " \"" + current_file + "\"" + " " + self.args
      print("Running " + incantation)
      subprocess.Popen(incantation, shell = True)
    elif self.cmd == "clean":
      incantation = "myke clean /S \"" + current_file + "\"" + " " + self.args
      print("Running " + incantation)
      subprocess.Popen(incantation, shell = True)
    elif self.cmd == "console_main":
      if (self.window.active_view() and self.window.active_view().settings().get("repl_external_id") == "myke_console"):
        self.window.run_command("next_view_in_stack")
      else:
        found = False
        for view in self.window.views():
          if view.settings().get("repl_external_id") == "myke_console":
            found = True
            self.window.focus_view(view)
        if not found:
          self.window.run_command("repl_open", {"type": "subprocess", "encoding": "utf8", "cmd": ["myke.exe", "/S", "console", self.args], "cwd": self.project_root, "external_id": "myke_console", "syntax": "Packages/Text/Plain Text.tmLanguage"})
    elif self.cmd == "console_new":
      self.window.run_command("repl_open", {"type": "subprocess", "encoding": "utf8", "cmd": ["myke.exe", "/S", "console", self.args], "cwd": self.project_root, "external_id": "myke_console", "syntax": "Packages/Text/Plain Text.tmLanguage"})
    elif self.cmd == "repl":
      self.window.run_command("repl_open", {"type": "subprocess", "encoding": "utf8", "cmd": ["myke.exe", "/S", "repl", self.args], "cwd": self.project_root, "external_id": "myke_repl", "syntax": "Packages/Scala/Scala.tmLanguage"})
    else:
      view_name = "myke " + self.cmd
      wannabes = filter(lambda v: v.name() == view_name, self.window.views())
      wannabe = wannabes[0] if len(wannabes) else self.window.new_file()
      wannabe.set_name(view_name)
      wannabe.settings().set("myke_project_root", self.project_root)
      wannabe.settings().set("myke_current_file", self.current_file)
      wannabe.settings().set("myke_args", self.args)
      self.window.run_command("exec", {"title": "myke " + self.cmd, "cmd": ["myke", "/S", self.cmd, self.current_file, self.args], "cont": "myke_continuation", "shell": "true", "working_dir": self.current_dir, "file_regex": "weird value stubs", "line_regex": "are necessary for sublime"})

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
