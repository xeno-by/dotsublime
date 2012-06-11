import os
from sublime import *
from sublime_plugin import *
from ensime_api import EnsimeApi
from ensime_environment import get_ensime_env
from ensime_repl import EnsimeReplBase

class EnsimeBase(object):
  def __init__(self, owner):
    if type(owner) == Window:
      self.env = get_ensime_env(owner)
      self.w = owner
      self.v = owner.active_view()
      self.f = None
    elif type(owner) == View:
      self.env = get_ensime_env(owner.window())
      self.w = owner.window()
      self.v = owner
      self.f = owner.file_name()
    else:
      raise "unsupported owner of type: " + str(type(owner))

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

class EnsimeCommon(EnsimeBase, EnsimeReplBase, EnsimeApi):
  pass

class EnsimeWindowCommand(EnsimeCommon, WindowCommand):
  def __init__(self, window):
    EnsimeCommon.__init__(self, window)
    WindowCommand.__init__(self, window)

class EnsimeTextCommand(EnsimeCommon, TextCommand):
  def __init__(self, view):
    EnsimeCommon.__init__(self, view)
    TextCommand.__init__(self, view)
