from sublime_plugin import EventListener
from ensime_common import *

class ScalaOnly(EnsimeCommon):
  def is_enabled(self):
    return self.w and self.f and self.f.lower().endswith(".scala")

class NotRunningOnly(EnsimeCommon):
  def is_enabled(self):
    return not self.in_transition and self.valid and not (self.controller and self.controller.running)

class RunningOnly(EnsimeCommon):
  def is_enabled(self):
    return not self.in_transition and self.valid and self.controller.running

class ReadyEnsimeOnly(EnsimeCommon):
  def is_enabled(self):
    return not self.in_transition and self.valid and self.controller.ready

class ConnectedEnsimeOnly(EnsimeCommon):
  def is_enabled(self):
    return not self.in_transition and self.valid and self.controller.connected

class EnsimeContextProvider(EventListener):
  def on_query_context(self, view, key, operator, operand, match_all):
    return None
