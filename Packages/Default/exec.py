import sublime, sublime_plugin
import os, sys
import thread
import subprocess
import functools
import time
import signal
import re

class ProcessListener(object):
    def on_data(self, proc, data):
        pass

    def on_finished(self, proc):
        pass

# Encapsulates subprocess.Popen, forwarding stdout to a supplied
# ProcessListener (on a separate thread)
class AsyncProcess(object):
    def __init__(self, arg_list, env, listener,
            # "path" is an option in build systems
            path="",
            # "shell" is an options in build systems
            shell=False):

        self.listener = listener
        self.killed = False

        self.start_time = time.time()

        # Hide the console window on Windows
        startupinfo = None
        if os.name == "nt":
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

        # Set temporary PATH to locate executable in arg_list
        if path:
            old_path = os.environ["PATH"]
            # The user decides in the build system whether he wants to append $PATH
            # or tuck it at the front: "$PATH;C:\\new\\path", "C:\\new\\path;$PATH"
            os.environ["PATH"] = os.path.expandvars(path).encode(sys.getfilesystemencoding())

        proc_env = os.environ.copy()
        proc_env.update(env)
        for k, v in proc_env.iteritems():
            proc_env[k] = os.path.expandvars(v).encode(sys.getfilesystemencoding())

        self.proc = subprocess.Popen(arg_list, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, startupinfo=startupinfo, env=proc_env, shell=shell)

        if path:
            os.environ["PATH"] = old_path

        if self.proc.stdout:
            thread.start_new_thread(self.read_stdout, ())

        if self.proc.stderr:
            thread.start_new_thread(self.read_stderr, ())

    def kill(self):
        if not self.killed:
            self.killed = True
            self.proc.terminate()
            self.listener = None

    def poll(self):
        return self.proc.poll() == None

    def exit_code(self):
        return self.proc.poll()

    def read_stdout(self):
        while True:
            data = os.read(self.proc.stdout.fileno(), 2**15)

            if data != "":
                if self.listener:
                    self.listener.on_data(self, data)
            else:
                self.proc.stdout.close()
                if self.listener:
                    self.listener.on_finished(self)
                break

    def read_stderr(self):
        while True:
            data = os.read(self.proc.stderr.fileno(), 2**15)

            if data != "":
                if self.listener:
                    self.listener.on_data(self, data)
            else:
                self.proc.stderr.close()
                break

class ExecCommand(sublime_plugin.WindowCommand, ProcessListener):
    def run(self, cmd = [], file_regex = "", line_regex = "", working_dir = "",
            encoding = "utf-8", env = {}, quiet = False, kill = False,
            title = "", cont = "", #xeno.by
            # Catches "path" and "shell"
            **kwargs):

        if kill:
            if self.proc:
                self.proc.kill()
                self.proc = None
                self.output_view.settings().set("pid", "")
                self.append_data(None, "[Cancelled]")
            return

        #xeno.by: if not hasattr(self, 'output_view'):
        #    # Try not to call get_output_panel until the regexes are assigned
        #    # self.output_view = self.window.get_output_panel("exec")
        title = title or (cmd if type(cmd)==type(u"") else " ".join(cmd))
        wannabes = filter(lambda v: v.name() == title, self.window.views())
        self.output_view = wannabes[0] if len(wannabes) else self.window.new_file()
        # self.output_view = self.window.new_file()
        self.output_view.settings().set("no_history", True)
        self.output_view.set_name(title)
        self.output_view.set_scratch(True)
        self.output_view.show(self.output_view.size())
        self.output_view.set_read_only(False)
        edit = self.output_view.begin_edit()
        #if self.output_view.size(): self.output_view.insert(edit, self.output_view.size(), "\n\n")
        self.output_view.erase(edit, sublime.Region(0, self.output_view.size()))
        self.output_view.sel().clear()
        self.output_view.sel().add(sublime.Region(self.output_view.size()))
        self.output_view.end_edit(edit)
        self.output_view.set_read_only(True)

        #xeno.by: hack: would be much nicer if we could communicate with gaika about these
        # sure, it sets the regexes after the build, but that's not very convenient, especially given that we can press Ctrl+C before the build ends
        file_regex = file_regex if file_regex and file_regex != "dummy set by gaika" else "([:.a-z_A-Z0-9\\\\/-]+[.]scala):([0-9]+)"
        line_regex = line_regex if line_regex and line_regex != "dummy set by gaika" else ""

        # Default the to the current files directory if no working directory was given
        if (working_dir == "" and self.window.active_view()
                        and self.window.active_view().file_name()):
            working_dir = os.path.dirname(self.window.active_view().file_name())

        self.output_view.settings().set("result_file_regex", file_regex)
        self.output_view.settings().set("result_line_regex", line_regex)
        self.output_view.settings().set("result_base_dir", working_dir)

        # Call get_output_panel a second time after assigning the above
        # settings, so that it'll be picked up as a result buffer
        #xeno.by: self.window.get_output_panel("exec")
        other_view = self.window.new_file()
        self.window.focus_view(other_view)
        self.window.run_command("close_file")
        self.window.focus_view(self.output_view)

        self.encoding = encoding
        self.quiet = quiet

        self.proc = None
        if not self.quiet:
            print "Running " + " ".join(cmd)
            sublime.status_message("Running " + " ".join(cmd))

        #xeno.by: show_panel_on_build = sublime.load_settings("Preferences.sublime-settings").get("show_panel_on_build", True)
        #xeno.by: if show_panel_on_build:
        #xeno.by:     self.window.run_command("show_panel", {"panel": "output.exec"})

        merged_env = env.copy()
        if self.window.active_view():
            user_env = self.window.active_view().settings().get('build_env')
            if user_env:
                merged_env.update(user_env)

        # Change to the working dir, rather than spawning the process with it,
        # so that emitted working dir relative path names make sense
        if working_dir != "":
            os.chdir(working_dir)

        err_type = OSError
        if os.name == "nt":
            err_type = WindowsError

        try:
            # Forward kwargs to AsyncProcess
            self.proc = AsyncProcess(cmd, merged_env, self, **kwargs)
            self.output_view.settings().set("pid", self.proc.proc.pid)
            self.cont = cont
        except err_type as e:
            self.append_data(None, str(e) + "\n")
            self.append_data(None, "[cmd:  " + str(cmd) + "]\n")
            self.append_data(None, "[dir:  " + str(os.getcwdu()) + "]\n")
            if "PATH" in merged_env:
                self.append_data(None, "[path: " + str(merged_env["PATH"]) + "]\n")
            else:
                self.append_data(None, "[path: " + str(os.environ["PATH"]) + "]\n")
            if not self.quiet:
                self.append_data(None, "[Finished]")

    def is_enabled(self, kill = False):
        if kill:
            return hasattr(self, 'proc') and self.proc and self.proc.poll()
        else:
            return True

    def append_data(self, proc, data):
        if proc != self.proc:
            # a second call to exec has been made before the first one
            # finished, ignore it instead of intermingling the output.
            if proc:
                proc.kill()
            return

        try:
            str = data.decode(self.encoding)
        except:
            str = "[Decode error - output not " + self.encoding + "]"
            proc = None

        # Normalize newlines, Sublime Text always uses a single \n separator
        # in memory.
        str = str.replace('\r\n', '\n').replace('\r', '\n')

        selection_was_at_end = (len(self.output_view.sel()) == 1
            and self.output_view.sel()[0]
                == sublime.Region(self.output_view.size()))
        self.output_view.set_read_only(False)
        edit = self.output_view.begin_edit()
        self.output_view.insert(edit, self.output_view.size(), str)
        if selection_was_at_end:
            self.output_view.show(self.output_view.size())
        self.output_view.end_edit(edit)
        self.output_view.set_read_only(True)

    def finish(self, proc):
        if not self.quiet:
            elapsed = time.time() - proc.start_time
            exit_code = proc.exit_code()
            if exit_code == 0 or exit_code == None:
                self.append_data(proc, ("[Finished in %.1fs]") % (elapsed))
            else:
                self.append_data(proc, ("[Finished in %.1fs with exit code %d]") % (elapsed, exit_code))

            settings = sublime.load_settings("Exec.sublime-settings")
            for mask in settings.get("rules").keys():
                if re.match(mask, self.output_view.name()):
                    rule = settings.get("rules").get(mask)
                    if rule.get("autoclose") and exit_code == 0 or exit_code == None:
                        self.output_view.window().run_command("close_file")

        if proc != self.proc:
            return

        # Set the selection to the start, so that next_result will work as expected
        edit = self.output_view.begin_edit()
        self.output_view.sel().clear()
        self.output_view.sel().add(sublime.Region(0))
        self.output_view.end_edit(edit)

        if self.cont:
            self.output_view.run_command(self.cont, {"returncode": exit_code})

    def on_data(self, proc, data):
        sublime.set_timeout(functools.partial(self.append_data, proc, data), 0)

    def on_finished(self, proc):
        sublime.set_timeout(functools.partial(self.finish, proc), 0)

class ExecListener(sublime_plugin.EventListener):
  def on_close(self, view):
    pid = view.settings().get("pid")
    if pid:
      try:
        os.kill(int(pid), signal.SIGTERM)
      except OSError as ex:
        pass
