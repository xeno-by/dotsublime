import sublime
import os
import threading

envLock = threading.RLock()
ensime_envs = {}

def get_ensime_env(window):
  if window:
    envLock.acquire()
    try:
      return ensime_envs.get(window.id(), EnsimeEnvironment(window))
    finally:
      envLock.release()
  return None

class EnsimeEnvironment(object):
  def __init__(self, window):
    # plugin-wide stuff (immutable)
    self.settings = sublime.load_settings("Ensime.sublime-settings")
    server_dir = self.settings.get("ensime_server_path", "sublime_ensime\\server" if os.name == 'nt' else "sublime_ensime/server")
    server_path = server_dir if server_dir.startswith("/") or (":/" in server_dir) or (":\\" in server_dir) else os.path.join(sublime.packages_path(), server_dir)
    self.ensime_executable = server_path + '/' + ("bin\\server.bat" if os.name == 'nt' else "bin/server")
    self.plugin_root = server_path + "/.." # we can do better

    # instance-specific stuff (immutable)
    self.project_root = None
    self.project_file = None
    self.project_config = []
    prj_files = [(f + "/.ensime") for f in window.folders() if os.path.exists(f + "/.ensime")]
    if len(prj_files) > 0:
      self.project_file = prj_files[0]
      self.project_root = os.path.dirname(self.project_file)
      try:
        src = open(self.project_file).read() if self.project_file else "()"
        self.project_config = sexp.read(src)
        m = sexp.sexp_to_key_map(self.project_config)
        if m.get(":root-dir"):
          self.project_root = m[":root-dir"]
        else:
          self.project_config = self.project_config + [key(":root-dir"), self.project_root]
      except StandardError:
        pass
    self.valid = True

    # lifecycle (mutable)
    self.lifecycleLock = threading.RLock()
    self.in_transition = False
    self.controller = None

    # shared state (mutable)
    self.notes = []
    self.repl_last_insert = 0
    self.repl_last_fixup = 0
    self.repl_lock = threading.RLock()
    self.sv = window.get_output_panel("ensime_server")
    self.sv.set_name("ensime_server")
    self.sv.settings().set("word_wrap", True)
    self.cv = window.get_output_panel("ensime_client")
    self.cv.set_name("ensime_client")
    self.cv.settings().set("word_wrap", True)
    self.rv = window.get_output_panel("ensime_repl")
    self.rv.set_name("ensime_repl")
    self.rv.settings().set("word_wrap", True)
