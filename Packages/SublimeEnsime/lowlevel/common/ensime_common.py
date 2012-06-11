class EnsimeBase(object):
  def __init__(window):
    self.env = get_ensime_env(window)
    self.w = window
    self.v = window.get_active_view() if window else None

  def __init__(view):
    self.env = get_ensime_env(view)
    self.w = view.window() if view else None
    self.v = view
    self.f = view.file_name() if view else None

  def __getattr__(self, name):
    self.env.__getattribute__(name)

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
    if filename and filename.endswith("scala"):
      root = os.path.normcase(os.path.realpath(self.project_root))
      wannabe = os.path.normcase(os.path.realpath(filename))
      return wannabe.startswith(root)

class EnsimeCommon(EnsimeReplBase, EnsimeBase):
  pass
