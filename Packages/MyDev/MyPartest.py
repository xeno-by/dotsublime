import sublime, sublime_plugin
import os
from functools import partial as bind
from subprocess import call, Popen, PIPE

class MyPartestCreateCommand(sublime_plugin.WindowCommand):
  def run(self, flags):
    self.flags = flags
    self.window.show_quick_panel(self.test_types(), bind(self.on_selected))

  def test_types(self):
    return ["run", "neg", "pos"]

  def on_selected(self, index):
    if index != -1:
      self.test_type = self.test_types()[index]
      self.window.show_input_panel("Test name (" + self.test_type + "): ", "", self.on_entered, None, None)

  def on_entered(self, name):
    name = "files/" + self.test_type + "/" + name
    root = os.path.dirname(os.path.join(self.window.folders()[1], ".."))
    script = Popen(["partest-create", name] + (["--create-flags"] if self.flags else []), stdout=PIPE, cwd = root)
    output = script.communicate()[0].decode()[:-1]
    # call(["growlnotify", "-n", "Partest", "-m", output.replace("\n", " ").replace("/Users/xeno_by/Projects/", "")])
    if script.returncode == 0:
      created = map(lambda path: path[len("Created "):], output.splitlines())
      files = filter(os.path.isfile, created)
      files = filter(lambda path: not path.endswith(".check"), files)
      for file in files:
        self.window.open_file(file)
        # TODO: this thing doesn't work
        # self.window.run_command('reveal_in_side_bar')
