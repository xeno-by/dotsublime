import sublime, os, sys, traceback, json
from paths import *

def location(env):
  return env.session_file

def exists(env):
  return not not location(env)

class Breakpoint(object):
  def __init__(self, file_name, line):
    self.file_name = file_name or ""
    self.line = line or 0

  def is_meaningful(self):
    return self.file_name != "" or self.line != 0

  def is_valid(self):
    return not not self.file_name and self.line != None

class Launch(object):
  def __init__(self, name, main_class, args):
    self.name = name or ""
    self.main_class = main_class or ""
    self.args = args or ""

  def is_meaningful(self):
    return self.name != "" or self.main_class != "" or self.args != ""

  def is_valid(self):
    return not not self.main_class

  @property
  def command_line(self):
    cmdline = self.main_class
    if self.args:
      cmdline += (" " + self.args)
    return cmdline

class Session(object):
  def __init__(self, env, breakpoints, launches, launch_key):
    self.env = env
    self.breakpoints = breakpoints or []
    self.launches = launches or {}
    self.launch_key = launch_key or ""

  @property
  def launch_name(self):
    if self.launch_key: return "launch configuration \"" + self.launch_key + "\""
    else: return "launch configuration"

  @property
  def launch(self):
    return self.launches.get(self.launch_key, None)

def load(env):
  file_name = location(env)
  if file_name:
    try:
      session = None
      if os.path.exists(file_name):
        with open(file_name, "r") as f:
          contents = f.read()
          session = json.loads(contents)
      session = session or {}
      breakpoints = map(lambda b: Breakpoint(decode_path(b.get("file_name")), b.get("line")), session.get("breakpoints", []))
      breakpoints = filter(lambda b: b.is_meaningful(), breakpoints)
      launches_list = map(lambda c: Launch(c.get("name"), c.get("main_class"), c.get("args")), session.get("launch_configs", []))
      launches = {}
      # todo. this might lose user data
      for c in launches_list: launches[c.name] = c
      launch_key = session.get("current_launch_config") or ""
      return Session(env, breakpoints, launches, launch_key)
    except:
      print "Ensime: " + str(file_name) + " has failed to load"
      exc_type, exc_value, exc_tb = sys.exc_info()
      detailed_info = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
      print detailed_info
      return None
  else:
    return None

def save(env, data):
  file_name = location(env)
  if file_name:
    session = {}
    session["breakpoints"] = map(lambda b: {"file_name": encode_path(b.file_name), "line": b.line}, data.breakpoints)
    session["launch_configs"] = map(lambda c: {"name": c.name, "main_class": c.main_class, "args": c.args}, data.launches.values())
    session["current_launch_config"] = data.launch_key
    if not session["launch_configs"]:
      # create a dummy launch config, so that the user has easier time filling in the config
      session["launch_configs"] = [{"name": "", "main_class": "", "args": ""}]
    contents = json.dumps(session, sort_keys=True, indent=2)
    with open(file_name, "w") as f:
      f.write(contents)

def edit(env):
  env.w.open_file(location(env))

def load_launch(env):
  if not os.path.exists(env.session_file) or not os.path.getsize(env.session_file):
    message = "Launch configuration does not exist. "
    message += "Sublime will now create a configuration file for you. Do you wish to proceed?"
    if sublime.ok_cancel_dialog(message):
      env.save_session() # to pre-populate the config, so that the user has easier time filling it in
      env.w.run_command("ensime_show_session")
    return None

  session = env.load_session()
  if not session:
    message = "Launch configuration could not be loaded. "
    message += "Maybe the config is not accessible, but most likely it's simply not a valid JSON. "
    message += "\n\n"
    message += "Sublime will now open the configuration file for you to fix. "
    message += "If you don't know how to fix the config, delete it and Sublime will recreate it from scratch. "
    message += "Do you wish to proceed?"
    if sublime.ok_cancel_dialog(message):
      env.w.run_command("ensime_show_session")
    return None

  launch = session.launch
  if not launch:
    message = "Your current " + session.launch_name + " is not present. "
    message += "\n\n"
    message += "This means that the \"current_launch_config\" field of the config "
    if session.launch_key: config_status = "set to \"" + session.launch_key + "\""
    else: config_status = "set to an empty string"
    message += "(which is currently " + config_status + ") "
    message += "doesn't correspond to any entries in the \"launch_configs\" field of the config."
    message += "\n\n"
    message += "Sublime will now open the configuration file for you to fix. Do you wish to proceed?"
    if sublime.ok_cancel_dialog(message):
      env.w.run_command("ensime_show_session")
    return None

  if not launch.is_valid():
    message = "Your current " + session.launch_name + " doesn't specify the main class to start. "
    message += "\n\n"
    message += "This means that the entry with \"name\":  \"" + session.launch_key + "\" in the \"launch_configs\" field of the config "
    message += "does not have the \"main_class\" attribute set."
    message += "\n\n"
    message += "Sublime will now open the configuration file for you to fix. Do you wish to proceed?"
    if sublime.ok_cancel_dialog(message):
      env.w.run_command("ensime_show_session")
    return None

  return launch
