import sublime, sublime_plugin
import subprocess
import os
from _winreg import *

class MykeSelectTestSuiteCommand(sublime_plugin.WindowCommand):
  def run(self):
    self.load_suite_data()
    self.window.show_quick_panel(self.suites, self.suite_selected)

  def load_suite_data(self):
    self.exec_myke_command("myke /S get-test-suite")
    # read @"Software\Far2\KeyMacros\Vars\%%MykeCurrentTestSuite"
    # read @"Software\Far2\SavedDialogHistory\MykeTestSuites\Lines"
    self.current_suite = self.get_myke_env()["CurrentTestSuite"]
    self.suites = self.get_myke_test_suites()
    if self.current_suite in self.suites:
      i = self.suites.index(self.current_suite)
      self.suites.insert(0, self.suites.pop(i))

  def suite_selected(self, selected_index):
    if selected_index != -1:
      self.current_suite = self.suites[selected_index]
      self.update_suite_data()

  def update_suite_data(self):
    self.exec_myke_command("myke /S set-test-suite " + self.current_suite)

  def exec_myke_command(self, command):
    view = self.window.active_view()
    project_root = (view.settings().get("myke_project_root") if view else None) or self.window.folders()[0]
    current_file = (view.settings().get("myke_current_file") or view.file_name() if view else None) or project_root
    current_dir = view.settings().get("myke_current_file") or view.file_name() if view else None
    current_dir = os.path.dirname(current_dir) if current_dir else project_root
    subprocess.Popen(command, shell = True, cwd = current_dir)

  def get_myke_env(self):
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
    return env

  def get_myke_test_suites(self):
    hkcu = ConnectRegistry(None, HKEY_CURRENT_USER)
    key = OpenKey(hkcu, r"Software\Far2\SavedDialogHistory\MykeTestSuites", 0, KEY_ALL_ACCESS)
    raw = "error"
    for i in range(1024):
      try:
        name, value, t = EnumValue(key, i)
      except EnvironmentError:
        break
      if name == "Lines":
        raw = value
    CloseKey(key)
    CloseKey(hkcu)
    return raw
