from ensime_common import *
from ensime_filters import *

class EnsimeStartupCommand(NotRunningOnly, EnsimeWindowCommand):
  def run(self):
    EnsimeController(self).startup()

class EnsimeShutdownCommand(RunningOnly, EnsimeWindowCommand):
  def run(self):
    self.controller.shutdown()

class EnsimeShowClientMessagesCommand(ReadyEnsimeOnly, EnsimeWindowCommand):
  def run(self):
    self.view_show(self.cv, what)

class EnsimeShowServerMessagesCommand(ReadyEnsimeOnly, EnsimeWindowCommand):
  def run(self):
    self.view_show(self.sv, what)

# support `cls`
# rebind Enter, Escape, Backspace, Left, ShiftLeft, Home, ShiftHome
# persistent command history and Ctrl+Up/Ctrl+Down like in SublimeREPL
# completions for command names

class EnsimeShowClientServerReplCommand(ReadyEnsimeOnly, EnsimeWindowCommand):
  def __init__(self, window):
    self.visible = False
    self.window = window

  def run(self, toggle = True):
    self.visible = not self.visible if toggle else True
    if self.visible:
      self.repl_show()
    else:
      self.window.run_command("hide_panel", { "cancel": True })
