import sublime
import sublime_plugin
import os
import hashlib

settings = sublime.load_settings('BufferScroll.sublime-settings')

version = 3
version_current = settings.get('version', 0)
if version_current < version:
  settings.set('version', version)
  settings.set('buffers', {})
  settings.set('queue', [])
  sublime.save_settings('BufferScroll.sublime-settings')
  settings = sublime.load_settings('BufferScroll.sublime-settings')

buffers = settings.get('buffers', {})
queue = settings.get('queue', [])

class BufferScroll(sublime_plugin.EventListener):

  def on_load(self, view):
    if view.file_name() != None and view.file_name() != '':
      if unlock():
        print("buffer_scroll: on_load locked")
        return
      else:
        print("buffer_scroll: on_load unlocked")

      self.viewport_snapshot = view.viewport_position()
      print("buffer_scroll: before restore " + str(self.viewport_snapshot))
      sublime.set_timeout(lambda: self.restore(view), 100)

  # xeno.by: very stupid, yes, but that's the only way to keep the position
  # after the file has been reloaded because of external modifications
  def on_activated(self, view):
    skip = hasattr(self, "last_activated") and not filter(lambda view: view.id() == self.last_activated, view.window().views() if view.window() else [])
    self.last_activated = view.id()

    # xeno.by: we need to filter out on_activate after an overlay is closed
    # otherwise, ctrl+f becomes unusable, and so becomes ctrl+g
    if not skip:
      if view.file_name() != None and view.file_name() != '':
        if unlock():
          print("buffer_scroll: on_activated locked")
          return
        else:
          print("buffer_scroll: on_activated unlocked")

        self.viewport_snapshot = view.viewport_position()
        print("buffer_scroll: before restore " + str(self.viewport_snapshot))
        sublime.set_timeout(lambda: self.restore(view), 100)
    else:
      print("buffer_scroll: on_activated after quitting an overlay, skipped")

  # the application is not sending "on_close" event when closing
  # or switching the projects, then we need to save the data on focus lost
  def on_deactivated(self, view):
    if view.file_name() != None and view.file_name() != '':
      self.save(view)

  # save the data when background tabs are closed
  # these that don't receive "on_deactivated"
  def on_close(self, view):
    if view.file_name() != None and view.file_name() != '':
      self.save(view)

  # save data for focused tab when saving
  def on_pre_save(self, view):
    if view.file_name() != None and view.file_name() != '':
      self.save(view)

  def save(self, view):

    buffer = {}

    # timestamp
    buffer['t'] = os.path.getmtime(view.file_name())

    # scroll
    buffer['l'] = list(view.viewport_position())

    # selections
    buffer['s'] = []
    for r in view.sel():
      line_s, col_s = view.rowcol(r.a); line_e, col_e = view.rowcol(r.b)
      buffer['s'].append([view.text_point(line_s, col_s), view.text_point(line_e, col_e)])

    # marks
    buffer['m'] = []
    for r in view.get_regions("mark"):
      line_s, col_s = view.rowcol(r.a); line_e, col_e = view.rowcol(r.b)
      buffer['m'].append([view.text_point(line_s, col_s), view.text_point(line_e, col_e)])

    # bookmarks
    buffer['b'] = []
    for r in view.get_regions("bookmarks"):
      line_s, col_s = view.rowcol(r.a); line_e, col_e = view.rowcol(r.b)
      buffer['b'].append([view.text_point(line_s, col_s), view.text_point(line_e, col_e)])

    # folding
    buffer['f'] = []
    if int(sublime.version()) >= 2167:
      for r in view.folded_regions():
        line_s, col_s = view.rowcol(r.a); line_e, col_e = view.rowcol(r.b)
        buffer['f'].append([view.text_point(line_s, col_s), view.text_point(line_e, col_e)])
    else:
      folds = view.unfold(sublime.Region(0, view.size()))
      for r in folds:
        line_s, col_s = view.rowcol(r.a); line_e, col_e = view.rowcol(r.b)
        buffer['f'].append([view.text_point(line_s, col_s), view.text_point(line_e, col_e)])
      view.fold(folds)

    hash_filename = hashlib.sha1(os.path.normpath(view.file_name().encode('utf-8'))).hexdigest()[:7]
    hash_position = hash_filename+':'+str(view.window().get_view_index(view) if view.window() else '')

    buffers[hash_filename] = buffer
    buffers[hash_position] = buffer

    if hash_position in queue:
      queue.remove(hash_position)
    if hash_filename in queue:
      queue.remove(hash_filename)
    queue.append(hash_position)
    queue.append(hash_filename)
    if len(queue) > 2000:
      hash = queue.pop(0)
      del buffers[hash]
      hash = queue.pop(0)
      del buffers[hash]
    settings.set('buffers', buffers)
    settings.set('queue', queue)
    sublime.save_settings('BufferScroll.sublime-settings')

  def restore(self, view):
    hash_filename = hashlib.sha1(os.path.normpath(view.file_name().encode('utf-8'))).hexdigest()[:7]
    hash_position = hash_filename+':'+str(view.window().get_view_index(view) if view.window() else '')

    if hash_position in buffers:
      hash = hash_position
    else:
      hash = hash_filename

    if hash in buffers:
      buffer = buffers[hash]

      self.viewport_current = view.viewport_position()
      print("buffer_scroll: during restore " + str(self.viewport_current))
      if self.viewport_current != self.viewport_snapshot:
        mtime_saved = buffer['t']
        mtime_actual = str(os.path.getmtime(view.file_name()))
        print("buffer_scroll: mtime_saved " + str(mtime_saved))
        print("buffer_scroll: mtime_actual " + str(mtime_actual))

        if abs(float(mtime_saved) - float(mtime_actual)) < 10.0:
          print("buffer_scroll: detected intentional jump into buffer, restore cancelled")
          return
        else:
          print("buffer_scroll: detected reload due to external modifications, restore authorized")

      print("buffer_scroll: restore authorized " + str(buffer['l']))
      view.sel().clear()

      # fold
      rs = []
      for r in buffer['f']:
        rs.append(sublime.Region(int(r[0]), int(r[1])))
      if len(rs):
        view.fold(rs)

      # selection
      for r in buffer['s']:
        view.sel().add(sublime.Region(int(r[0]), int(r[1])))

      # marks
      rs = []
      for r in buffer['m']:
        rs.append(sublime.Region(int(r[0]), int(r[1])))
      if len(rs):
        view.add_regions("mark", rs, "mark", "dot", sublime.HIDDEN | sublime.PERSISTENT)

      # bookmarks
      rs = []
      for r in buffer['b']:
        rs.append(sublime.Region(int(r[0]), int(r[1])))
      if len(rs):
        view.add_regions("bookmarks", rs, "bookmarks", "bookmark", sublime.HIDDEN | sublime.PERSISTENT)

      # scroll
      if buffer['l']:
        view.set_viewport_position(tuple(buffer['l']), False)

lockfile = sublime.packages_path() + "/User/BufferScroll.lock"

def lock():
  with file(lockfile, "a"):
    os.utime(lockfile, None)

def unlock():
  def do_unlock():
    try:
      if os.path.exists(lockfile):
        os.remove(lockfile)
    except IOError as e:
      pass

  locked = os.path.exists(lockfile)
  if locked:
    sublime.set_timeout(do_unlock, 200)
    return True
  else:
    return False
