import sublime, sublime_plugin

class MyCleanCommand(sublime_plugin.WindowCommand):
  def run(self):
    self.window.show_quick_panel(self.targets, self.on_selected)

  @property
  def quick(self):
    return map(lambda target: "quick/" + target, ["compiler+reflect", "compiler", "reflect", "library"])

  @property
  def targets(self):
    return self.quick + ["all"]

  def on_selected(self, index):
    target = self.targets[index]
    self.window.run_command("gaika", {"cmd": "clean", "args": [target]})
