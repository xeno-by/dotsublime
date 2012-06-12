import os
from sublime import *
from sublime_plugin import *
from ensime_api import EnsimeApi
from ensime_log import EnsimeLog
from ensime_environment import get_ensime_env

class EnsimeBase(object):
  def __init__(self, owner):
    self.owner = owner
    if type(owner) == Window:
      self.env = get_ensime_env(owner)
      self.w = owner
      self.v = owner.active_view()
      self.f = None
    elif type(owner) == View:
      self.env = get_ensime_env(owner.window() or sublime.active_window())
      self.w = owner.window()
      self.v = owner
      self.f = owner.file_name()
    else:
      raise "unsupported owner of type: " + str(type(owner))

  def in_project(filename):
    if filename and filename.endswith("scala"):
      root = os.path.normcase(os.path.realpath(self.env.project_root))
      wannabe = os.path.normcase(os.path.realpath(filename))
      return wannabe.startswith(root)

class EnsimeCommon(EnsimeBase, EnsimeLog, EnsimeApi):
  pass

def ensime_api(owner):
  return EnsimeCommon(owner)

class EnsimeWindowCommand(EnsimeCommon, WindowCommand):
  pass

class EnsimeTextCommand(EnsimeCommon, TextCommand):
  pass

class ScalaOnly:
  def is_enabled(self):
    return self.w and self.f and self.f.lower().endswith(".scala")

class NotRunningOnly:
  def is_enabled(self):
    return not self.env.in_transition and self.env.valid and not (self.env.controller and self.env.controller.running)

class RunningOnly:
  def is_enabled(self):
    return not self.env.in_transition and self.env.valid and self.env.controller and self.env.controller.running

class ReadyEnsimeOnly:
  def is_enabled(self):
    return not self.env.in_transition and self.env.valid and self.env.controller and self.env.controller.ready

class ConnectedEnsimeOnly:
  def is_enabled(self):
    return not self.env.in_transition and self.env.valid and self.env.controller and self.env.controller.connected

class EnsimeContextProvider(EventListener):
  def on_query_context(self, view, key, operator, operand, match_all):
    if key == "ensime_ready":
      try:
        return ensime_api(view).env.controller.ready
      except:
        return False
    if key == "ensime_connected":
      try:
        return ensime_api(view).env.controller.connected
      except:
        return False
    return None
