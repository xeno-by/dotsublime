import sublime, sublime_plugin
from functools import partial as bind

class MyCommandClickCommand(sublime_plugin.TextCommand):
  # note the underscore in "run_"
  def run_(self, edit, args):
    self.v = self.view
    self.old_sel = [(r.a, r.b) for r in self.v.sel()]
    # unfortunately, running an additive drag_select is our only way of getting the coordinates of the click
    # I didn't find a way to convert args["event"]["x"] and args["event"]["y"] to text coordinates
    # there are relevant APIs, but they refuse to yield correct results
    self.v.run_command("drag_select", {"event": args["event"], "additive": True})
    self.new_sel = [(r.a, r.b) for r in self.v.sel()]
    self.diff = list((set(self.old_sel) - set(self.new_sel)) | (set(self.new_sel) - set(self.old_sel)))

    if len(self.diff) == 0:
      if len(self.new_sel) == 1:
        self.run(self.new_sel[0][0])
      else:
        # this is a tough one
        # here's how we possibly could arrive here
        # we have a multi selection, and then ctrl+click on one the active cursors
        # there's no way we can guess the exact point of click, so we bail
        pass
    elif len(self.diff) == 1:
      sel = self.v.sel()
      sel.clear()
      sel.add(sublime.Region(self.diff[0][0], self.diff[0][1]))
      sublime.set_timeout(bind(self.v.window().run_command, "goto_definition"), 100)
    else:
      # this shouldn't happen
      self.log("len(diff) > 1: command = " + str(type(self)) + ", old_sel = " + str(self.old_sel) + ", new_sel = " + str(self.new_sel))
