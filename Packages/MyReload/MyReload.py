import os
import sublime
from sublime_plugin import EventListener

class MyReload(EventListener):
  def on_post_save(self, view):
    w = view.window()
    f = view and view.file_name()
    f = os.path.normcase(os.path.realpath(f)) if f else None
    t = os.path.normcase(os.path.realpath(os.path.join(sublime.packages_path(), "SublimeEnsime")))
    if f and f.startswith(t):
      print "reloading sublime-ensime"
      for dirname, dirnames, filenames in os.walk(t):
        for filename in filenames:
          os.utime(os.path.join(dirname, filename), None)
      if w: w.run_command("ensime_startup")
