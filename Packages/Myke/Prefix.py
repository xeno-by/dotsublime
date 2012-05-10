import sublime, sublime_plugin
from _winreg import *
import os

class MykePrefixCommand(sublime_plugin.WindowCommand):
  def run(self):
    settings = MykeSettings()
    if settings.require_prefix:
      settings.persistent_require_prefix = not settings.persistent_require_prefix
    settings.require_prefix = True
    settings.save()

# how do I reuse a class between multiple files?
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