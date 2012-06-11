import sublime_plugin, sublime
import functools, socket, threading
import sexp
from string import strip
from sexp import key, sym

class EnsimeClientListener:
  def on_client_async_data(self, data):
    pass

  def on_disconnect(self, reason):
    pass

class EnsimeClientSocket(EnsimeCommon):
  def __init__(self, port, handlers):
    self.port = port
    self.connected = False
    self.disconnect_pending = False
    self.handlers = handlers
    self._lock = threading.RLock()
    self._connect_lock = threading.RLock()
    self._receiver = None

  def notify_async_data(self, data):
    for handler in self.handlers:
      handler.on_client_async_data(data)

  def notify_disconnect(self, reason):
    for handler in self.handlers:
      handler.on_disconnect(reason)

  def receive_loop(self):
    while self.connected:
      try:
        res = self.socket.recv(4096)
        self.log_client("RECV: " + unicode(res, "utf-8"))
        if res:
          len_str = res[:6]
          msglen = int(len_str, 16) + 6
          msg = res[6:msglen]
          nxt = strip(res[msglen:])
          while len(nxt) > 0 or len(msg) > 0:
            form = sexp.read(msg)
            sublime.set_timeout(functools.partial(self.notify_async_data, form), 0)
            if len(nxt) > 0:
              msglen = int(nxt[:6], 16) + 6
              msg = nxt[6:msglen]
              nxt = strip(nxt[msglen:])
            else:
              msg = ""
              msglen = ""
        else:
          self.connected = False
      except Exception as e:
        self.log_client("*****    ERROR     *****")
        self.log_client("expected disconnect" if self.disconnect_pending else "unexpected disconnect")
        self.log_client(e)
        reason = "server" if not self.disconnect_pending else "client"
        self.disconnect_pending = False
        self.notify_disconnect(reason)
        self.connected = False

  def start_receiving(self):
    t = threading.Thread(name = "ensime-client-" + str(self.window.id()) + "-" + str(self.port), target = self.receive_loop)
    t.setDaemon(True)
    t.start()
    self._receiver = t

  def connect(self):
    self._connect_lock.acquire()
    try:
      s = socket.socket()
      s.connect(("127.0.0.1", self.port))
      self.socket = s
      self.connected = True
      self.start_receiving()
      return s
    except socket.error as e:
      # set sublime error status
      self.connected = False
      sublime.error_message("Can't connect to ensime server:  " + e.args[1])
    finally:
      self._connect_lock.release()

  def send(self, request):
    try:
      if not self.connected:
        self.connect()
      self.socket.send(request)
    except:
      self.notify_disconnect("server")
      self.set_connected(False)

  def sync_send(self, request, msg_id):
    self._connect_lock.acquire()
    try:
      s = socket.socket()
      s.connect(("127.0.0.1", self.port))
      try:
        s.send(request)
        result = ""
        keep_going = True
        nxt = ""
        while keep_going:
          res = nxt + s.recv(4096)
          msglen = int(res[:6], 16) + 6
          msg = res[6:msglen]
          if (len(msg) + 6) == msglen:
            nxt = strip(res[msglen:])
            while len(nxt) > 0 or len(msg) > 0:
              if len(nxt) > 0:
                sublime.set_timeout(functools.partial(self.notify_async_data, sexp.read(msg)), 0)
                msglen = int(nxt[:6], 16) + 6
                msg = nxt[6:msglen]
                nxt = strip(nxt[msglen:])
              else:
                nxt = ""
                break
            result = sexp.read(msg)
            keep_going = result == None or msg_id != result[-1]
            if keep_going:
              sublime.set_timeout(functools.partial(self.notify_async_data, result), 0)
          else:
            nxt = res

        return result
      except Exception as error:
        self.log_client(error)
      finally:
        if s:
          s.close()
    except Exception as error:
      self.log_client(error)
    finally:
      self._connect_lock.release()

  def close(self):
    self._connect_lock.acquire()
    try:
      if self.socket:
        self.socket.close()
      self.connect = False
    finally:
      self._connect_lock.release()
