import sublime, sublime_plugin
import os, tempfile
from subprocess import call, PIPE

class MyDiffFirstConflictCommand(sublime_plugin.TextCommand):
  def run(self, edit):
    v = self.view
    lines = v.substr(sublime.Region(0, v.size())).split("\n")
    # print(lines)
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
      houtput, foutput = tempfile.mkstemp("", "output.")
      os.write(hlocal, local.encode())
      os.write(hbase, base.encode())
      os.write(hremote, remote.encode())
      call(["open", "-a", "Araxis Merge"])
      call(["/usr/local/bin/araxisgitmerge", fremote, fbase, flocal])
      # os.spawnlp(os.P_NOWAIT, "/usr/local/bin/ksdiff", "/usr/local/bin/ksdiff", "--merge", "--output", foutput, "--base", fbase, fremote, flocal)
    else:
      sublime.status_message("Merge conflicts not found")

class MyDiffAutoCompareCommand(sublime_plugin.TextCommand):
  def diff(self, file1, file2):
    call(["open", "-a", "Araxis Merge"])
    call(["/usr/local/bin/araxisopendiff", file1, file2])

  def run(self, edit):
    v = self.view
    w = v.window()
    if (len(w.views()) < 2):
      pass
    elif (len(w.views()) == 2):
      self.diff(w.views()[0].file_name(), w.views()[1].file_name())
    else:
      self.this_file = v.file_name()
      self.other_files = []
      for other_v in w.views():
        if v.id() != other_v.id() and other_v.file_name():
          self.other_files.append(other_v.file_name())
      w.show_quick_panel(self.other_files, self.on_selected)

  def on_selected(self, index):
    if index != -1:
      self.diff(self.this_file, self.other_files[index])





