import sublime, sublime_plugin
import os, re, shutil
from functools import partial as bind
from subprocess import Popen, PIPE

class MyHackCommand(sublime_plugin.ApplicationCommand):
  def activate_or_deactivate_project_window(self):
    for window in sublime.windows():
      if window.folders():
        if self.home in window.folders():
          if self.delete:
            print "self-destruct!!!"
            window.run_command("close")
          else:
            # activate this window
            # but how???
            # anyways we're fine, since for now it's enough to just close the extraneous empty window
            pass
      else:
        if not window.views():
          window.run_command("close")

  def generate_snippets_if_necessary(self):
    pass

  def run(self):
    with open(os.path.expandvars("$HOME/.hack_sublime"), "r") as f:
      lines = f.read().splitlines()
      self.target = lines[0]
      self.home = lines[1] + "/sandbox"
    self.add, self.delete = self.target.startswith("+"), self.target.startswith("-")
    if self.add or self.delete: self.target = self.target[1:]
    self.activate_or_deactivate_project_window()
    self.generate_snippets_if_necessary()

class MySandboxSnippetCommand(sublime_plugin.WindowCommand):
  def __init__(self, window):
    sublime_plugin.WindowCommand.__init__(self, window)

  def run(self):
    for folder in self.window.folders():
      if folder.endswith("sandbox"):
        if os.listdir(folder):
          self.window.show_quick_panel(["Yes, clean " + folder, "No, don't delete anything"], bind(self.on_selected, folder))
        else:
          self.on_selected(folder, 0)

  def cleanup(self, folder):
    for path in os.listdir(folder):
      path = os.path.join(folder, path)
      if os.path.isfile(path):
        print "Removing file " + path
        os.unlink(path)
      else:
        print "Removing directory " + path
        shutil.rmtree(path)

  def on_selected(self, folder, selection):
    if selection == 0:
      self.cleanup(folder)
      self.generate(folder)

  def generate(self, folder):
    flavor = re.match("^MySandbox(?P<flavor>.*?)SnippetCommand$", self.__class__.__name__).expand("\g<flavor>")
    files = map(lambda name: sublime.packages_path() + "/MyHack/" + flavor + "/" + name, self.list_files())
    for source in files:
      template = open(os.path.expandvars(source)).read()
      template = os.path.expandvars(template)
      marker = "HERE"
      line, pos = None, None
      if marker in template:
        lines = template.splitlines()
        line = (i for i,line in enumerate(lines) if marker in line).next()
        pos = lines[line].find(marker)
      template = template.replace("HERE", "")
      destination = folder + "/" + os.path.basename(source)
      with open(destination, "w") as f: f.write(template)
      if line != None:
        view = self.window.open_file(destination + ":" + str(line + 1) + ":" + str(pos + 1), sublime.ENCODED_POSITION)

class MySandboxVanillaSnippetCommand(MySandboxSnippetCommand):
  def list_files(self):
    return ["Test.scala"]

class MySandboxMacroSnippetCommand(MySandboxSnippetCommand):
  def list_files(self):
    return ["Macros.scala", "Test.scala"]
