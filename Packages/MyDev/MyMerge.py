import sublime, sublime_plugin
import os, tempfile
from subprocess import call, PIPE

class MyDiffFirstConflictCommand(sublime_plugin.TextCommand):
  def run(self, edit):
    v = self.view
    lines = v.substr(sublime.Region(0, v.size())).split("\n")
    print(lines)
    def find(prefix):
      try: return (i for i,v in enumerate(lines) if v.startswith(prefix)).__next__()
      except: return -1
    start_local = find("<<<<<<<")
    start_base = find("|||||||")
    start_remote = find("=======")
    finish = find(">>>>>>>")
    # print lines
    # print (start_local, start_base, start_remote, finish)
    if start_local != -1:
      local = "\n".join(lines[start_local + 1 : start_base])
      base = "\n".join(lines[start_base + 1 : start_remote])
      remote = "\n".join(lines[start_remote + 1 : finish])
      hlocal, flocal = tempfile.mkstemp("", "mine.")
      hbase, fbase = tempfile.mkstemp("", "parent.")
      hremote, fremote = tempfile.mkstemp("", "theirs.")
      os.write(hlocal, local.encode())
      os.write(hbase, base.encode())
      os.write(hremote, remote.encode())
      call(["open", "-a", "Araxis Merge"])
      call(["/usr/local/bin/araxisgitmerge", fremote, fbase, flocal])
