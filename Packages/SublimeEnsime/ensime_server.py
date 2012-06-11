import os, re
from ensime_common import *
from ensime_server_process import EnsimeServerListener, EnsimeServerProcess

class EnsimeServer(EnsimeServerListener, EnsimeCommon):
  def __init__(self, owner, port_file):
    super(type(self).__mro__[0], self).__init__(owner)
    self.port_file = port_file

  def startup(self):
    ensime_command = self.get_ensime_command()
    self.log_server("Launching ENSIME server process with: " + str(ensime_command))
    self.proc = EnsimeServerProcess(self.owner, ensime_command, [self, self.env.controller])

  def get_ensime_command(self):
    if not os.path.exists(self.env.ensime_executable):
      sublime.error_message("Ensime executable \"" + self.env.ensime_executable + "\" does not exist. Check your Ensime.sublime-settings.")
      return
    return [self.env.ensime_executable, self.port_file]

  def on_server_data(self, data):
    str_data = str(data).replace("\r\n", "\n").replace("\r", "\n")
    self.view_insert(self.env.sv, str_data)

  def shutdown(self):
    self.proc.kill()
    self.proc = None
    self.view_insert(self.env.sv, "[Shut down]")
