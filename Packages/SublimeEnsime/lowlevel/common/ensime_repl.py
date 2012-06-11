import sublime
import functools

class EnsimeReplBase:
  def __init__():
    self.prompt = "ensime>"
    self.fixup_timeout = 500

  def view_insert(self, v, what):
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
    self.window.run_command("show_panel", {"panel": "output." + v.name()})
    if focus:
      self.window.focus_view(v)
    sublime.set_timeout(functools.partial(v.show, v.size()), 100)

  def repl_show(self):
    self.repl_lock.acquire()
    try:
      last = self.env.repl_last_insert
      current = self.rv.size()
      if (last == current):
        self.repl_insert(self.prompt, False)
      self.view_show(self.rv, what, True)
    finally:
      self.repl_lock.release()

  def repl_insert(self, what, rewind = True):
    self.repl_lock.acquire()
    try:
      selection_was_at_end = (len(self.rv.sel()) == 1 and self.rv.sel()[0] == sublime.Region(self.rv.size()))
      was_read_only = self.rv.is_read_only()
      self.rv.set_read_only(False)
      edit = self.rv.begin_edit()
      last = self.env.repl_last_insert
      current = self.rv.size()
      if rewind:
        user_input = ""
        if current - last >= len(self.prompt):
          user_input = self.rv.substr(sublime.Region(last + len(self.prompt), current))
      self.rv.insert(edit, current, what)
      if rewind:
        self.env.repl_last_insert = self.rv.size()
        if current - last >= len(self.prompt):
          self.repl_schedule_fixup(user_input, self.env.repl_last_insert)
      if selection_was_at_end:
        self.rv.show(self.rv.size())
        self.rv.sel().clear()
        self.rv.sel().add(sublime.Region(self.rv.size()))
      self.rv.end_edit(edit)
      self.rv.set_read_only(was_read_only)
    finally:
      self.repl_lock.release()

  def repl_schedule_fixup(self, what, last_insert):
    sublime.set_timeout(functools.partial(self.repl_insert_fixup, what, last_insert), self.fixup_timeout)

  def repl_insert_fixup(self, what, last_insert):
    self.repl_lock.acquire()
    try:
      if self.env.repl_last_fixup < last_insert:
        self.env.repl_last_fixup = last_insert
        if self.env.repl_last_insert == last_insert:
          selection_was_at_end = (len(self.rv.sel()) == 1 and self.rv.sel()[0] == sublime.Region(self.rv.size()))
          was_read_only = self.rv.is_read_only()
          self.rv.set_read_only(False)
          edit = self.rv.begin_edit()
          self.rv.insert(edit, self.rv.size(), self.prompt + what)
          if selection_was_at_end:
            self.rv.show(self.rv.size())
            self.rv.sel().clear()
            self.rv.sel().add(sublime.Region(self.rv.size()))
          self.rv.end_edit(edit)
          self.rv.set_read_only(was_read_only)
        self.repl_schedule_fixup(what, self.env.repl_last_insert)
    finally:
      self.repl_lock.release()

  def repl_get_input(self):
    self.repl_lock.acquire()
    try:
      last = self.env.repl_last_insert
      current = self.rv.size()
      return self.rv.substr(sublime.Region(last, current))[len(self.prompt):]
    finally:
      self.repl_lock.release()
