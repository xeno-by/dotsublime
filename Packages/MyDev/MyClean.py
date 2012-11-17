import sublime, sublime_plugin
import os, shutil
from subprocess import call

class MyCleanCommand(sublime_plugin.WindowCommand):
  def run(self):
    self.window.show_quick_panel(self.targets, self.on_selected)

  @property
  def quick(self):
    return map(lambda target: "quick/" + target, ["compiler", "reflect", "lib"])

  @property
  def targets(self):
    return self.quick + ["all"]

  def on_selected(self, index):
    target = self.targets[index]
    if target.startswith("quick/"):
      self.clean_quick(target[len("quick/"):])
    elif target == "all":
      map(lambda target: clean_quick(target), self.quick)
    else:
      print "Unknown clean target: " + target

  def clean_quick(self, target):
    root = os.path.join(self.window.folders()[1], "..")
    quick = os.path.join(root, "build/quick")
    complete = os.path.join(quick, target + ".complete")
    classes = os.path.join(quick, "classes/" + target)
    if os.path.exists(complete): os.unlink(complete)
    if os.path.exists(classes): shutil.rmtree(classes)
    call(["growlnotify", "-n", "Kepler", "-m", "Cleaned quick/" + target])
