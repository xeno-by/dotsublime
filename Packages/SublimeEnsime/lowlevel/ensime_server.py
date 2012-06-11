import os, re
from ensime_server_process import EnsimeServerListener, EnsimeServerProcess

class EnsimeServer(EnsimeServerListener, EnsimeCommon):
  def startup(self):
    ensime_command = self.get_ensime_command()
    self.log_server("Launching ENSIME server process with: " + str(ensime_command))
    self.proc = EnsimeServerProcess(ensime_command, [self, self.controller])

  def get_ensime_command(self):
    if not os.path.exists(self.ensime_executable):
      sublime.error_message("Ensime executable \"" + self.ensime_executable + "\" does not exist. Check your Ensime.sublime-settings.")
      return
    _, port_file = tempfile.mkstemp("ensime_port")
    self.port_file = port_file
    return [self.ensime_executable, port_file]

  def on_server_data(self, data):
    str_data = str(data).replace("\r\n", "\n").replace("\r", "\n")
    self.view_insert(self.sv, strdata)
    if not self.ready and re.search("Wrote port", str_data):
      self.ready = True
      self.controller.handshake()

  def shutdown(self):
    try:
      self.proc.kill()
      self.proc = None
      self.append_data(None, "[Cancelled]")
    except:
      self.log_server("Error shutting down:")
      self.log_server(sys.exc_info()[1])
