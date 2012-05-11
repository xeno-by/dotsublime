# courtesy of: https://gist.github.com/1251716
# saved from: http://pastie.org/private/bclbdgxzbkb1gs2jfqzehg

import sublime
import sublime_plugin
import subprocess

class MyFilterCommand(sublime_plugin.TextCommand):
  """
  Runs an external command with the selected text,
  which will then be replaced by the command output.
  """
  def run(self, edit):
    self.edit = edit
    self.window = self.view.window()
    self.settings = FilterSettings()
    self.window.show_input_panel("Filter through:", self.settings.last_command or "", self.command_input, None, None)

  def command_input(self, command):
    edit = self.edit
    view = self.view

    self.settings.last_command = command
    self.settings.save()

    if view.sel()[0].empty():
      # nothing selected: process the entire file
      region = sublime.Region(0L, view.size())
    else:
      # process only selected region
      region = view.line(view.sel()[0])

    p = subprocess.Popen(
      command,
      shell=True,
      bufsize=-1,
      stdout=subprocess.PIPE,
      stderr=subprocess.PIPE,
      stdin=subprocess.PIPE)

    output, error = p.communicate(view.substr(region).encode('utf-8'))

    if error:
      sublime.error_message(error.decode('utf-8'))
    else:
      view.replace(edit, region, output.decode('utf-8'))

class FilterSettings(object):
  def __init__(self):
    settings = sublime.load_settings("MyFilter.sublime-settings")
    self.last_command = settings.get("last_command")

  def save(self):
    settings = sublime.load_settings("MyFilter.sublime-settings")
    settings.set("last_command", self.last_command)
    sublime.save_settings("MyFilter.sublime-settings")
