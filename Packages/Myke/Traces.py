import sublime, sublime_plugin
import subprocess
import os
import re

class MykeLastTrace(sublime_plugin.WindowCommand):
  def run(self):
    file = ImportantMykeTraces().last()
    if file:
      self.window.open_file(file)

class MykePrevTrace(sublime_plugin.WindowCommand):
  def run(self):
    file = ImportantMykeTraces().prev()
    if file:
      self.window.open_file(file)

class MykeNextTrace(sublime_plugin.WindowCommand):
  def run(self):
    file = ImportantMykeTraces().next()
    if file:
      self.window.open_file(file)

class ImportantMykeTraces(object):
  def __init__(self):
    self.load_from_settings()

  def load_from_settings(self):
    global_settings = sublime.load_settings("ImportantMykeTraces.sublime-settings")
    settings = global_settings.get(str(os.getpid())) or {}
    self.last_trace = settings.get("last_trace", None)

  def save_to_settings(self):
    global_settings = sublime.load_settings("ImportantMykeTraces.sublime-settings")
    settings = {}
    settings["last_trace"] = self.last_trace
    global_settings.set(str(os.getpid()), settings)
    sublime.save_settings("ImportantMykeTraces.sublime-settings")

  def list_files(self):
    from stat import S_ISREG, ST_CTIME, ST_MODE
    import os, sys, time, glob
    search_dir = r"C:\Users\xeno.by\.myke_important"
    files = filter(os.path.isfile, glob.glob(search_dir + "\\*.log"))
    files.sort(key = lambda x: x)
    files.reverse()
    return files

  def last(self):
    files = self.list_files()
    self.last_trace = files[0] if len(files) else ""
    self.save_to_settings()
    return self.last_trace

  def prev(self):
    files = self.list_files()
    if self.last_trace in files:
      iof = files.index(self.last_trace)
      if iof + 1 < len(files):
        iof = iof + 1
      self.last_trace = files[iof]
      self.save_to_settings()
      return self.last_trace
    else:
      self.last()

  def next(self):
    files = self.list_files()
    if self.last_trace in files:
      iof = files.index(self.last_trace)
      if iof > 0:
        iof = iof - 1
      self.last_trace = files[iof]
      self.save_to_settings()
      return self.last_trace
    else:
      self.last()

class MykeSmartTraceLoader(sublime_plugin.EventListener):
  def on_load(self, view):
    if view.file_name() and view.file_name().startswith(r"C:\Users\xeno.by\.myke_important"):
      # myke<WSP>rebuild<WSP>C:\Projects\KeplerUnderRefactoring<WSP>args
      first_line = view.substr(view.line(sublime.Region(0, 0)))
      m = re.search(r"myke (.*?) (.*)", first_line)
      if m:
        action = m.group(1)
        targs = m.group(2)
        if not targs.startswith("\""):
          iof = targs.index(" ")
          target = targs[:iof]
          s_args = targs[(iof + 1):]
        else:
          iof = targs.index("\"", 1)
          target = targs[:iof][1:-1]
          s_args = targs[(iof + 2):]
        args = s_args.split(" ") if s_args else []
        # print "target = " + target
        # print "args = " + str(args)

        view.settings().set("myke_command", action)
        view.settings().set("myke_current_file", target)
        view.settings().set("myke_args", args)
        view.settings().set("result_file_regex", "([:.a-z_A-Z0-9\\\\/-]+[.]scala):([0-9]+)")
        view.settings().set("result_line_regex", "")
        view.settings().set("result_base_dir", "")

        # this is necessary for result_* settings to be applied
        window = view.window()
        other_view = window.new_file()
        window.focus_view(other_view)
        window.run_command("close_file")
        window.focus_view(view)