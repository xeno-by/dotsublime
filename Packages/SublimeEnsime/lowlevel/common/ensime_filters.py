class ScalaOnly(EnsimeCommon):
  def is_enabled(self):
    file_name = self.window.active_view().file_name()
    return bool(self.window and file_name != "" and self._is_scala(file_name))

  def _is_scala(self, file_name):
    _, fname = os.path.split(file_name)
    return fname.lower().endswith(".scala")

class NotRunningOnly(EnsimeCommon):
  def is_enabled(self):
    return not self.env.in_transition and self.env.valid and not self.env.running

class RunningOnly(EnsimeCommon):
  def is_enabled(self):
    return not self.env.in_transition and self.env.valid and self.env.running

class EnsimeOnly(EnsimeCommon):
  def is_enabled(self):
    return not self.env.in_transition and self.env.valid and self.env.ready

class ConnectedEnsimeOnly(EnsimeCommon):
  def is_enabled(self):
    return not self.env.in_transition and self.env.valid and self.env.connected

class EnsimeContextProvider(sublime_plugin.EventListener):
  def on_query_context(view, key, operator, operand, match_all):
    return None