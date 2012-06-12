import os
import sublime
import functools

class EnsimeLog(object):

  def log(self, data):
    sublime.set_timeout(functools.partial(self.log_on_ui_thread, "ui", data), 0)

  def log_client(self, data, to_disk_only = False):
    sublime.set_timeout(functools.partial(self.log_on_ui_thread, "client", data, to_disk_only), 0)

  def log_server(self, data, to_disk_only = False):
    sublime.set_timeout(functools.partial(self.log_on_ui_thread, "server", data, to_disk_only), 0)

  def log_on_ui_thread(self, flavor, data, to_disk_only):
    if flavor in self.env.settings.get("log_to_console", {}):
      if not to_disk_only:
        print str(data)
    if flavor in self.env.settings.get("log_to_file", {}):
      try:
        if not os.path.exists(self.env.log_root):
          os.mkdir(self.env.log_root)
        file_name = os.path.join(self.env.log_root, flavor + ".log")
        with open(file_name, "a") as f: f.write(data + "\n")
      except:
        pass

  def view_insert(self, v, what):
    sublime.set_timeout(functools.partial(self.view_insert_on_ui_thread, v, what), 0)

  def view_insert_on_ui_thread(self, v, what):
    selection_was_at_end = (len(v.sel()) == 1 and v.sel()[0] == sublime.Region(v.size()))
    v.set_read_only(False)
    edit = v.begin_edit()
    v.insert(edit, v.size(), what)
    if selection_was_at_end:
      v.show(v.size())
    v.end_edit(edit)
    v.set_read_only(True)
    self.repl_insert(what)

  def view_show(self, v, focus = False):
    self.w.run_command("show_panel", {"panel": "output." + v.name()})
    if focus:
      self.w.focus_view(v)
    sublime.set_timeout(functools.partial(v.show, v.size()), 100)

  def repl_prompt(self):
    return "ensime>"

  def repl_fixup_timeout(self):
    return 500

  def repl_show(self):
    self.env.repl_lock.acquire()
    try:
      last = self.env.repl_last_insert
      current = self.env.rv.size()
      if (last == current):
        self.repl_insert(self.repl_prompt(), False)
      self.view_show(self.env.rv, True)
    finally:
      self.env.repl_lock.release()

  def repl_insert(self, what, rewind = True):
    sublime.set_timeout(functools.partial(self.repl_insert_on_ui_thread, what, rewind), 0)

  def repl_insert_on_ui_thread(self, what, rewind):
    self.env.repl_lock.acquire()
    try:
      selection_was_at_end = (len(self.env.rv.sel()) == 1 and self.env.rv.sel()[0] == sublime.Region(self.env.rv.size()))
      was_read_only = self.env.rv.is_read_only()
      self.env.rv.set_read_only(False)
      edit = self.env.rv.begin_edit()
      last = self.env.repl_last_insert
      current = self.env.rv.size()
      if rewind:
        user_input = ""
        if current - last >= len(self.repl_prompt()):
          user_input = self.env.rv.substr(sublime.Region(last + len(self.repl_prompt()), current))
      self.env.rv.insert(edit, current, what)
      if rewind:
        self.env.repl_last_insert = self.env.rv.size()
        if current - last >= len(self.repl_prompt()):
          self.repl_schedule_fixup(user_input, self.env.repl_last_insert)
      if selection_was_at_end:
        self.env.rv.show(self.env.rv.size())
        self.env.rv.sel().clear()
        self.env.rv.sel().add(sublime.Region(self.env.rv.size()))
      self.env.rv.end_edit(edit)
      self.env.rv.set_read_only(was_read_only)
    finally:
      self.env.repl_lock.release()

  def repl_schedule_fixup(self, what, last_insert):
    sublime.set_timeout(functools.partial(self.repl_insert_fixup, what, last_insert), self.repl_fixup_timeout())

  def repl_insert_fixup(self, what, last_insert):
    self.env.repl_lock.acquire()
    try:
      if self.env.repl_last_fixup < last_insert:
        self.env.repl_last_fixup = last_insert
        if self.env.repl_last_insert == last_insert:
          selection_was_at_end = (len(self.env.rv.sel()) == 1 and self.env.rv.sel()[0] == sublime.Region(self.env.rv.size()))
          was_read_only = self.env.rv.is_read_only()
          self.env.rv.set_read_only(False)
          edit = self.env.rv.begin_edit()
          self.env.rv.insert(edit, self.env.rv.size(), self.repl_prompt() + what)
          if selection_was_at_end:
            self.env.rv.show(self.env.rv.size())
            self.env.rv.sel().clear()
            self.env.rv.sel().add(sublime.Region(self.env.rv.size()))
          self.env.rv.end_edit(edit)
          self.env.rv.set_read_only(was_read_only)
        self.repl_schedule_fixup(what, self.env.repl_last_insert)
    finally:
      self.env.repl_lock.release()

  def repl_get_input(self):
    self.env.repl_lock.acquire()
    try:
      last = self.env.repl_last_insert
      current = self.env.rv.size()
      return self.env.rv.substr(sublime.Region(last, current))[len(self.repl_prompt()):]
    finally:
      self.env.repl_lock.release()
