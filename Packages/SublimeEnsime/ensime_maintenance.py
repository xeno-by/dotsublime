from ensime_common import *
from ensime_controller import EnsimeController

class EnsimeStartupCommand(NotRunningOnly, EnsimeWindowCommand):
  def run(self):
    EnsimeController(self.w).startup()

class EnsimeShutdownCommand(RunningOnly, EnsimeWindowCommand):
  def run(self):
    self.env.controller.shutdown()

class EnsimeRestartCommand(RunningOnly, EnsimeWindowCommand):
  def run(self):
    self.w.run_command("ensime_shutdown")
    self.w.run_command("ensime_startup")

class EnsimeShowClientMessagesCommand(ReadyEnsimeOnly, EnsimeWindowCommand):
  def run(self):
    self.view_show(self.env.cv, False)

class EnsimeShowServerMessagesCommand(ReadyEnsimeOnly, EnsimeWindowCommand):
  def run(self):
    self.view_show(self.env.sv, False)

# support `cls`
# rebind Enter, Escape, Backspace, Left, ShiftLeft, Home, ShiftHome
# persistent command history and Ctrl+Up/Ctrl+Down like in SublimeREPL

class EnsimeShowClientServerReplCommand(ReadyEnsimeOnly, EnsimeWindowCommand):
  def __init__(self, window):
    super(type(self).__mro__[0], self).__init__(window)
    self.visible = False
    self.window = window

  def run(self, toggle = True):
    self.visible = not self.visible if toggle else True
    if self.visible:
      self.repl_show()
    else:
      self.window.run_command("hide_panel", { "cancel": True })
