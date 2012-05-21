import sublime, sublime_plugin
import subprocess
import os
from _winreg import *

class MykeCommand(sublime_plugin.WindowCommand):
  def run(self, cmd = "compile", args = [], repeat_last = False):
    window = self.window
    view = self.window.active_view()
    self.view = view
    if self.view:
      row, col = self.view.rowcol(self.view.sel()[0].a)
      self.linum = str(row + 1)
    self.settings = MykeSettings()
    if repeat_last:
      self.cmd = self.settings.last_command
      self.project_root = self.settings.last_project_root
      self.current_file = self.settings.last_current_file
      self.current_dir = self.settings.last_current_dir
      self.args = self.settings.last_args
      if self.cmd:
        self.launch_myke()
    else:
      self.cmd = cmd
      self.args = args or (view.settings().get("myke_args") if view else None) or []

      # how do I reliably detect currently open project?!
      self.project_root = (view.settings().get("myke_project_root") if view else None) or self.window.folders()[0]
      self.current_file = (view.settings().get("myke_current_file") or view.file_name() if view else None) or self.project_root
      self.current_dir = view.settings().get("myke_current_file") or view.file_name() if view else None
      self.current_dir = os.path.dirname(self.current_dir) if self.current_dir else self.project_root
      if view and view.settings().get("repl_external_id") == "myke_console":
        contents = view.substr(sublime.Region(0, view.size()))
        last_line = view.substr(view.lines(sublime.Region(0, view.size()))[-1])[0:-1]
        self.current_file = last_line

      if self.settings.require_prefix:
        if not self.settings.persistent_require_prefix:
          self.settings.require_prefix = False
          self.settings.save()
        self.window.show_input_panel("Command prefix:", self.settings.last_prefix or "", self.prefix_input, None, None)
      else:
        self.launch_myke()

  def prefix_input(self, prefix):
    self.settings.last_prefix = prefix
    self.settings.save()
    view = self.window.active_view()
    self.args = self.args + prefix.split(" ")
    self.launch_myke()

  def menuitem_selected(self, selected_index):
    if selected_index != -1:
      menuitem = self.menu[selected_index]
      hotkey = menuitem[:1]
      print "hotkey is " + hotkey
      if hotkey == "s":
        self.window.show_quick_panel(["Yes, run build in Jenkins", "No, cancel this command"], self.jenkins_confirmed)
      elif hotkey == "x":
        self.run("menu", [menuitem, self.current_file + "#L" + self.linum])
      elif hotkey == "c":
        self.run("menu", [menuitem, self.current_file + "#L" + self.linum])
      else:
        self.run("menu", [menuitem])

  def jenkins_confirmed(self, selected_index):
    if selected_index == 0:
      self.run("menu", ["s. Build in Jenkins"])

  def launch_myke(self):
    if self.cmd == "menu":
      if not self.args:
        incantation = "myke /S menu" + (" " if len(self.args) > 0 else "") + " ".join(self.args)
        print("Running " + incantation + " at " + self.current_dir)
        p = subprocess.Popen(incantation, shell = True, stdout = subprocess.PIPE, cwd = self.current_dir)
        output, _ = p.communicate()
        self.menu = output.split('\r\n')[:-1]
        self.window.show_quick_panel(self.menu, self.menuitem_selected)
        return

    if self.cmd == "smart-logall" or self.cmd == "smart-commit":
      incantation = "myke /S " + self.cmd
      if len(self.args) > 0:
        incantation = incantation + " " + " ".join(self.args)
      print("Running " + incantation + " at " + self.current_dir)
      subprocess.Popen(incantation, shell = True, cwd = self.current_dir)
    elif self.cmd == "smart-blame" or self.cmd == "smart-logthis":
      incantation = "myke /S " + self.cmd + " \"" + self.current_file + "\""
      if len(self.args) > 0:
        incantation = incantation + " " + " ".join(self.args)
      print("Running " + incantation + " at " + self.current_file)
      subprocess.Popen(incantation, shell = True)
    elif self.cmd == "clean":
      incantation = "myke clean /S \"" + self.current_file + "\""
      if len(self.args) > 0:
        incantation = incantation + " " + " ".join(self.args)
      print("Running " + incantation + " at " + self.current_dir)
      subprocess.Popen(incantation, shell = True, cwd = self.current_dir)
    # elif self.cmd == "console_main":
    #   if (self.window.active_view() and self.window.active_view().settings().get("repl_external_id") == "myke_console"):
    #     self.window.run_command("next_view_in_stack")
    #   else:
    #     found = False
    #     for view in self.window.views():
    #       if view.settings().get("repl_external_id") == "myke_console":
    #         found = True
    #         self.window.focus_view(view)
    #     if not found:
    #       self.window.run_command("repl_open", {"type": "subprocess", "encoding": "utf8", "cmd": ["myke.exe", "/S", "console"] + self.args, "cwd": self.current_dir, "external_id": "myke_console", "syntax": "Packages/Text/Plain Text.tmLanguage"})
    elif self.cmd == "console_new":
      self.window.run_command("repl_open", {"type": "subprocess", "encoding": "utf8", "cmd": ["myke.exe", "/S", "console"] + self.args, "cwd": self.current_dir, "external_id": "myke_console", "syntax": "Packages/Text/Plain Text.tmLanguage"})
    elif self.cmd == "repl":
      self.window.run_command("repl_open", {"type": "subprocess", "encoding": "utf8", "cmd": ["myke.exe", "/S", "repl"] + self.args, "cwd": self.current_dir, "external_id": "myke_repl", "syntax": "Packages/Text/Plain Text.tmLanguage"})
    else:
      view_name = "myke " + self.cmd
      if self.cmd == "menu":
        menuitem = self.args[0]
        hotkey = menuitem[:1]
        caption = menuitem[3:]
        caption = caption[:1].lower() + caption[1:]
        view_name = "myke " + caption
        self.args[0] = hotkey
      wannabes = filter(lambda v: v.name() == view_name, self.window.views())
      wannabe = wannabes[0] if len(wannabes) else self.window.new_file()
      wannabe.set_name(view_name)
      wannabe.settings().set("myke_project_root", self.project_root)
      wannabe.settings().set("myke_current_file", self.current_file)
      wannabe.settings().set("myke_args", self.args)
      self.settings.last_command = self.cmd
      self.settings.last_project_root = self.project_root
      self.settings.last_current_file = self.current_file
      self.settings.last_current_dir = self.current_dir
      self.settings.last_args = self.args
      self.settings.save()
      cmd = ["myke", "/S", self.cmd, self.current_file] + self.args
      cmd = cmd[:3] + cmd[4:] if self.cmd == "menu" or self.cmd == "remote" or self.cmd.startswith("smart") else cmd
      self.window.run_command("exec", {"title": view_name, "cmd": cmd, "cont": "myke_continuation", "shell": "true", "working_dir": self.current_dir, "file_regex": "weird value stubs", "line_regex": "are necessary for sublime"})

  def load_settings(self):
    return

class MykeSettings(object):
  def __init__(self):
    self.init_from_sublime_settings()

  def init_from_sublime_settings(self):
    global_settings = sublime.load_settings("Myke.sublime-settings")
    settings = global_settings.get(str(os.getpid())) or {}
    self.last_command = settings.get("last_command", None)
    self.last_project_root = settings.get("last_project_root", None)
    self.last_current_file = settings.get("last_current_file", None)
    self.last_current_dir = settings.get("last_current_dir", None)
    self.last_args = settings.get("last_args", None)
    self.last_prefix = settings.get("last_prefix", None)
    self.require_prefix = settings.get("require_prefix", False)
    self.persistent_require_prefix = settings.get("persistent_require_prefix", False)

  def init_from_registry(self):
    hkcu = ConnectRegistry(None, HKEY_CURRENT_USER)
    key = OpenKey(hkcu, r"Software\Far2\KeyMacros\Vars", 0, KEY_ALL_ACCESS)
    env = {}
    for i in range(1024):
      try:
        name, value, t = EnumValue(key, i)
      except EnvironmentError:
        break
      if name.startswith("%%Settings"):
        env[name[10:]] = value
    CloseKey(key)
    CloseKey(hkcu)
    self.last_command = env.get("LastCommand")
    self.last_project_root = env.get("LastProjectRoot")
    self.last_current_file = env.get("LastCurrentFile")
    self.last_current_dir = env.get("LastCurrentDir")
    self.last_args = (env.get("LastArgs") or "").split(" ")
    self.last_prefix = env.get("LastPrefix")
    self.require_prefix = bool(env.get("RequirePrefix"))
    self.persistent_require_prefix = bool(env.get("PersistentRequirePrefix"))
    return env

  def save(self):
    self.save_to_sublime_settings()

  def save_to_sublime_settings(self):
    global_settings = sublime.load_settings("Myke.sublime-settings")
    settings = {}
    settings["last_command"] = self.last_command
    settings["last_current_file"] = self.last_current_file
    settings["last_project_root"] = self.last_project_root
    settings["last_current_dir"] = self.last_current_dir
    settings["last_args"] = self.last_args
    settings["last_prefix"] = self.last_prefix
    settings["require_prefix"] = self.require_prefix
    settings["persistent_require_prefix"] = self.persistent_require_prefix
    global_settings.set(str(os.getpid()), settings)
    sublime.save_settings("Myke.sublime-settings")

  def save_to_registry(self):
    hkcu = ConnectRegistry(None, HKEY_CURRENT_USER)
    key = OpenKey(hkcu, r"Software\Far2\KeyMacros\Vars", 0, KEY_ALL_ACCESS)
    env = {}
    try:
      SetValueEx(key, "%%SettingsLastCommand", 0, REG_SZ, str(self.last_command or ""))
      SetValueEx(key, "%%SettingsLastProjectRoot", 0, REG_SZ, str(self.last_project_root or ""))
      SetValueEx(key, "%%SettingsLastCurrentFile", 0, REG_SZ, str(self.last_current_file or ""))
      SetValueEx(key, "%%SettingsLastCurrentDir", 0, REG_SZ, str(self.last_current_dir or ""))
      SetValueEx(key, "%%SettingsLastArgs", 0, REG_SZ, " ".join(self.last_args or []))
      SetValueEx(key, "%%SettingsLastPrefix", 0, REG_SZ, str(self.last_prefix or ""))
      SetValueEx(key, "%%SettingsRequirePrefix", 0, REG_SZ, str("True" if self.require_prefix else ""))
      SetValueEx(key, "%%SettingsPersistentRequirePrefix", 0, REG_SZ, str("True" if self.persistent_require_prefix else ""))
    except EnvironmentError:
      print "Encountered problems writing into the Registry..."
    CloseKey(key)
    CloseKey(hkcu)
    return env

class MykeBangBangCommand(sublime_plugin.WindowCommand):
  def run(self):
    self.window.run_command("myke", {"repeat_last": True})

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

    success = True if env["Status"] == "0" else False
    meaningful = env["Meaningful"] == "1" if "Meaningful" in env else None
    if success and not meaningful:
      window.run_command("close_file")

    result_file_regex = env["ResultFileRegex"] if "ResultFileRegex" in env else ""
    result_line_regex = env["ResultLineRegex"] if "ResultLineRegex" in env else ""
    working_dir = env["WorkingDir"]
    if result_file_regex or result_line_regex:
      view.settings().set("result_file_regex", result_file_regex)
      view.settings().set("result_line_regex", result_line_regex)
      view.settings().set("result_base_dir", env["WorkingDir"])
      window.focus_view(view)

    view.settings().erase("no_history")
#    pt = view.text_point(1, 1)
#    view.sel().clear()
#    view.sel().add(sublime.Region(pt))
#    view.show(pt)

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
