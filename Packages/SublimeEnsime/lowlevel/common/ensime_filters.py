class ScalaOnly(EnsimeCommon):
  def is_enabled(self):
    return self.w and self.f and self.f.lower().endswith(".scala")

class NotRunningOnly(EnsimeCommon):
  def is_enabled(self):
    return not self.in_transition and self.valid and not (self.controller and self.controller.running)

class RunningOnly(EnsimeCommon):
  def is_enabled(self):
    return not self.in_transition and self.valid and self.controller.running

class EnsimeOnly(EnsimeCommon):
  def is_enabled(self):
    return not self.in_transition and self.valid and self.controller.ready

class ConnectedEnsimeOnly(EnsimeCommon):
  def is_enabled(self):
    return not self.in_transition and self.valid and self.controller.connected

class EnsimeContextProvider(sublime_plugin.EventListener):
  def on_query_context(view, key, operator, operand, match_all):
    return None