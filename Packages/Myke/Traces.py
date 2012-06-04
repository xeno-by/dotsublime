import sublime, sublime_plugin
import subprocess
import os

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
