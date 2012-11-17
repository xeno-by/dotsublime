import sublime, sublime_plugin
import time
import os
from collections import deque

MAX_SIZE = 64
LINE_THRESHOLD = 2
TIME_THRESHOLD = 1000
DEBUG = False

class Location(object):
    """A location in the history
    """

    def __init__(self, path, line, col):
        self.time = time.time() * 1000
        self.path = path
        self.line = line
        self.col = col

    def __eq__(self, other):
        return self.path == other.path and self.line == other.line

    def __ne__(self, other):
        return not self.__eq__(other)

    def __nonzero__(self):
        return (self.path is not None and self.line is not None)

    def near(self, other):
        return self.path == other.path and abs(self.line - other.line) <= LINE_THRESHOLD

    def copy(self):
        return Location(self.path, self.line, self.col)

    def __str__(self):
        return str(self.path) + ":" + str(self.line) + ":" + str(self.col)

class History(object):
    """Keep track of the history for a single window
    """

    def __init__(self, max_size=MAX_SIZE):
        self._current = None                # current location as far as the
                                            # history is concerned
        self._back = deque([], max_size)    # items before self._current
        self._forward = deque([], max_size) # items after self._current

        self._record_movement_invoked = 0   # number of times `record_movement' has been invoked
        self._last_movement = None          # last recorded movement
        self._last_history = None           # last recorded movement that got into history
        self._last_navigation = None        # last recorded navigation (alt+left or alt+right)

    def record_movement(self, location):
        """Record movement to the given location, pushing history if
        applicable
        """

        if location:
            if self.has_changed(location):
                if DEBUG:
                    print("nav_history: " + str(location))

                if self._current:
                    time_delta = abs(location.time - self._current.time)
                    if DEBUG:
                        print "nav_history: subsume? old = " + str(self._current)
                        print "nav_history: subsume? new = " + str(location) + " (" + str(time_delta) + " ms)"
                    subsume = self._current.path == location.path and time_delta <= TIME_THRESHOLD
                    # subsume = time_delta <= TIME_THRESHOLD
                    if subsume:
                        if DEBUG:
                            print("nav_history: subsumed")
                        if self.has_changed(location):
                            self._current = location
                            self._last_movement = location.copy()
                            self._last_history = location.copy()
                        else:
                            if DEBUG:
                                print("nav_history: discarded both")
                            prev = self._back and self._back.pop()
                            if prev:
                                self._last_movement = prev.copy()
                            self._current = prev
                            self._last_history = location.copy()
                    else:
                        if DEBUG:
                            print("nav_history: didn't subsume")
                        self.push(location)
                        self._last_movement = location.copy()
                        self._last_history = location.copy()
                else:
                    self.push(location)
                    self._last_movement = location.copy()
                    self._last_history = location.copy()
            else:
                self._last_movement = location.copy()

    def has_changed(self, location):
        """Determine if the given location combination represents a
        significant enough change to warrant pushing history.
        """

        changed_movement = self._last_movement is None or not self._last_movement.near(location)
        changed_history = self._last_history is None or not self._last_history.near(location)
        changed_navigation = self._last_navigation is None or not self._last_navigation.near(location)
        return changed_movement and changed_history and changed_navigation

    def push(self, location):
        """Push the given location to the back history. Clear the forward
        history.
        """

        if self._current is not None:
            self._back.append(self._current.copy())
        self._current = location.copy()
        self._forward.clear()

    def back(self):
        """Move backward in history, returning the location to jump to.
        Returns None if no history.
        """

        if not self._back:
            return None

        self._forward.appendleft(self._current)
        self._current = self._back.pop()
        self._last_movement = self._current # preempt, so we don't re-push

        self._last_navigation = self._current
        return self._current

    def forward(self):
        """Move forward in history, returning the location to jump to.
        Returns None if no history.
        """

        if not self._forward:
            return None

        self._back.append(self._current)
        self._current = self._forward.popleft()
        self._last_movement = self._current # preempt, so we don't re-push

        self._last_navigation = self._current
        return self._current

_histories = {} # window id -> History

def get_history():
    """Get a History object for the current window,
    creating a new one if required
    """

    window = sublime.active_window()
    if window is None:
        return None

    window_id = window.id()
    history = _histories.get(window_id, None)
    if history is None:
        _histories[window_id] = history = History()
    return history

class PrintNavigationHistory(sublime_plugin.WindowCommand):
    def run(self):
        history = get_history()
        if history is None:
            return

        print("=====")
        for entry in history._back:
            print(str(entry.path) + ":" + str(entry.line) + ":" + str(entry.col))
        print("* " + str(history._current.path) + ":" + str(history._current.line) + ":" + str(history._current.col))
        for entry in history._forward:
            print(str(entry.path) + ":" + str(entry.line) + ":" + str(entry.col))
        print("=====")

class NavigationHistoryRecorder(sublime_plugin.EventListener):
    """Keep track of history
    """

    def on_selection_modified(self, view):
        if not view.sel():
            pass

        # filters out temporary navs from ctrl+f and ctrl+g
        active_view_id = view.window() and view.window().active_view() and view.window().active_view().id()
        if hasattr(self, "_last_activated") and self._last_activated and self._last_activated != active_view_id:
            if DEBUG:
                print("nav_history: on_selection_modified when an overlay is active, skipped")
            return

        self.possiblyRecordMovement(view)

    def on_activated(self, view):
        self._last_activated = view.id()
        self.possiblyRecordMovement(view)

    def possiblyRecordMovement(self, view):
        """When the selection is changed, possibly record movement in the
        history
        """
        history = get_history()
        if history is None:
            return

        if view.settings().get("repl") or view.settings().get("no_history"):
            return

        is_not_previewed = False
        window = sublime.active_window()
        for window_view in window.views():
            if (window_view.id() == view.id()):
                is_not_previewed = True

        if is_not_previewed:
            path = view.file_name()
            if not path and view.name(): path = view.id()
            if path:
                if len(view.sel()) == 0:
                    if DEBUG:
                        print("nav_history: empty view.sel(), skipped")
                else:
                    if len(view.sel()) > 1:
                        if DEBUG:
                            print("nav_history: multiple selections, using view.sel()[0]")
                    row, col = view.rowcol(view.sel()[0].a)
                    history.record_movement(Location(path, row + 1, col + 1))


    # def on_close(self, view):
    #     """When a view is closed, check to see if the window was closed too
    #     and clean up orphan histories
    #     """
    #
    #     # XXX: This doesn't work - event runs before window is removed
    #     # from sublime.windows()
    #
    #     windows_with_history = set(_histories.keys())
    #     window_ids = set([w.id() for w in sublime.windows()])
    #     closed_windows = windows_with_history.difference(window_ids)
    #     for window_id in closed_windows:
    #         del _histories[window_id]

class NavigationHistoryBack(sublime_plugin.TextCommand):
    """Go back in history
    """

    def run(self, edit):
        history = get_history()
        if history is None:
            return

        location = history.back()
        if location:
            lock_buffer_scroll()
            if DEBUG:
                print("back to: " + str(location.path) + ":" + str(location.line) + ":" + str(location.col))

            window = sublime.active_window()
            if not isinstance(location.path, int):
                window.open_file("%s:%d:%d" % (location.path, location.line, location.col), sublime.ENCODED_POSITION)
            else:
                found = False
                for view in window.views():
                    if view.id() == location.path:
                        found = True
                        window.focus_view(view)
                        pt = view.text_point(location.line, location.col)
                        view.sel().clear()
                        view.sel().add(sublime.Region(pt))
                        view.show(pt)
                if not found:
                    window.run_command("navigation_history_backward")
        else:
            if DEBUG:
                print("back to: None")
            pass

class NavigationHistoryForward(sublime_plugin.TextCommand):
    """Go forward in history
    """

    def run(self, edit):
        history = get_history()
        if history is None:
            return

        location = history.forward()
        if location:
            lock_buffer_scroll()
            if DEBUG:
                print("forward to: " + str(location.path) + ":" + str(location.line) + ":" + str(location.col))

            window = sublime.active_window()
            if not isinstance(location.path, int):
                window.open_file("%s:%d:%d" % (location.path, location.line, location.col), sublime.ENCODED_POSITION)
            else:
                found = False
                for view in window.views():
                    if view.id() == location.path:
                        found = True
                        window.focus_view(view)
                        pt = view.text_point(location.line, location.col)
                        view.sel().clear()
                        view.sel().add(sublime.Region(pt))
                        view.show(pt)
                if not found:
                    window.run_command("navigation_history_forward")
        else:
            if DEBUG:
                print("forward to: None")
            pass

bufferscroll_lockfile = sublime.packages_path() + "/User/BufferScroll.lock"

def lock_buffer_scroll():
    with file(bufferscroll_lockfile, "a"):
        os.utime(bufferscroll_lockfile, None)

def unlock_buffer_scroll():
    def do_unlock():
        try:
            if os.path.exists(bufferscroll_lockfile):
                os.remove(bufferscroll_lockfile)
        except IOError as e:
            pass

    locked = os.path.exists(bufferscroll_lockfile)
    if locked:
        sublime.set_timeout(do_unlock, 200)
        return True
    else:
        return False
