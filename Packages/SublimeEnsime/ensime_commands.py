from ensime_common import *

class EnsimeInspectTypeAtPoint(EnsimeTextCommand):
  def run(self, edit):
    self.inspect_type_at_point(self.f, self.view.sel()[0].begin(), self.handle_reply)

  def handle_reply(self, tpe):
    if tpe:
      self.view.set_status("ensime-typer", tpe)
    else:
      self.view.erase_status("ensime-typer")
