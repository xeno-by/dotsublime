# conversion from EnsimeBase to bool (equivalent of saying `self.env.connected`)
# use method_missing functionality to redirect stuff from EnsimeCommon to EnsimeEnvironment

class EnsimeBase(object):
  def __init__(window):
    self.env = get_env(window)
    self.w = window
    self.v = window.get_active_view() if window else None

  def __init_(view):
    self.env = get_env(view)
    self.w = view.window() if view else None
    self.v = view

  def log(self, data):
    if "highlevel" in self.settings.get("log", {}):
      print str(data)

  def log_client(self, data):
    if "client" in self.settings.get("log", {}):
      print str(data)

  def log_server(self, data):
    if "server" in self.settings.get("log", {}):
      print str(data)

  def in_project(filename):
    if not self.connected:
      return False
    if filename and filename.endswith("scala"):
      root = os.path.normcase(os.path.realpath(self.project_root))
      wannabe = os.path.normcase(os.path.realpath(filename))
      return wannabe.startswith(root)

class EnsimeCommon(EnsimeBase, EnsimeReplBase):
  pass
