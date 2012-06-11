from ensime_common import *

class EnsimeInspectTypeAtPoint(ConnectedEnsimeOnly, EnsimeTextCommand):
  def run(self, edit):
    self.inspect_type_at_point(self.f, self.v.sel()[0].begin(), self.handle_reply)

  def handle_reply(self, tpe):
    if tpe:
      self.v.set_status("ensime-typer", tpe)
    else:
      self.v.erase_status("ensime-typer")
