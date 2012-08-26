import sublime, os, traceback, functools, sys
from functools import partial as bind
import sexp
from sexp import key, sym
from paths import *

def locations(window):
  """Intelligently guess the appropriate .ensime file locations for the
  given window. Return: list of possible locations."""
  return [(f + os.sep + ".ensime") for f in window.folders() if os.path.exists(f + os.sep + ".ensime")]

def exists(window):
  """Determines whether a .ensime file exists in one of the locations
  expected by `load`."""
  return len(locations(window)) != 0

def load(window):
  """Intelligently guess the appropriate .ensime file location for the
  given window. Load the .ensime and parse as s-expression.
  Return: (inferred project root directory, config sexp)
  """
  for f in locations(window):
    root = encode_path(os.path.dirname(f))
    src = "()"
    with open(f) as open_file:
      src = open_file.read()
    try:
      conf = sexp.read_relaxed(src)
      m = sexp.sexp_to_key_map(conf)
      if m.get(":root-dir"):
        root = m[":root-dir"]
      else:
        conf = conf + [key(":root-dir"), root]
      return (root, conf, None)
    except:
      return (None, None, bind(error_bad_config, window, f, sys.exc_info()))
  return (None, None, bind(error_no_config, window))

def error_no_config(window):
  message = "Ensime has been unable to start, because you haven't yet created an Ensime project in this Sublime workspace."
  message += "\n\n"
  message += "Sublime will now try to create a project for you. Do you wish to proceed?"
  if sublime.ok_cancel_dialog(message):
    create(window)

def error_bad_config(window, f, ex):
  exc_type, exc_value, exc_tb = ex
  detailed_info = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
  print detailed_info
  message = "Ensime has failed to parse the .ensime configuration file at " + str(f) + " because of the following error: "
  message += "\n\n"
  message += (str(exc_type) + ": "+ str(exc_value))
  message += ("\n" + "(for detailed info refer to Sublime console)")
  message += "\n\n"
  message += "Sublime will now open the offending configuration file for you to fix. Do you wish to proceed?"
  if sublime.ok_cancel_dialog(message):
    create(window)

def create(window):
  class DotensimeCreator(object):
    def __init__(self, window):
      self.w = window

    def do_create(self):
      if len(self.w.folders()) == 0:
        message = "Ensime project cannot be created, because you either don't have a Sublime project "
        message += "or don't have any folders associated with your Sublime project."
        message += "\n\n"
        message += "To use Ensime you need to have an active non-empty project. "
        message += "Sublime will now try to initialize a project for you. "
        message += "\n\n"
        message += "You will be shown a dialog that will let you select a root folder for the project. "
        message += "After the root folder is selected, Sublime will create a configuration file in it. "
        message += "Do you wish to proceed?"
        if sublime.ok_cancel_dialog(message):
          self.w.run_command("prompt_add_folder")
          # if you don't do set_timeout, self.w.folders() won't be updated
          sublime.set_timeout(self.post_prompt_add_folder, 0)
          return

      if len(self.w.folders()) > 1:
        message = "A .ensime configuration file needs to be created in one of your project's folders."
        message += "\n\n"
        message += "Since you have multiple folders in the project, pick an appropriate folder in the dialog that will follow."
        sublime.message_dialog(message)

      if (len(self.w.folders())) == 1:
        self.folder_selected(0)
      else:
        self.w.show_quick_panel(self.w.folders(), self.folder_selected)

    def post_prompt_add_folder(self):
      if len(self.w.folders()) != 0:
        self.do_create()

    def folder_selected(self, selected_index):
      if selected_index != -1:
        target_folder = self.w.folders()[selected_index]
        v = self.w.open_file(target_folder + os.sep + ".ensime")
        if not v.size():
          # we have to do this in such a perverse way
          # because direct v.begin_edit() won't work
          sublime.set_timeout(bind(self.fill_in_with_mock_config, target_folder, v.file_name()), 0)

    def fill_in_with_mock_config(self, target_folder, path):
      for v in self.w.views():
        if v.file_name() == path:
          e = v.begin_edit()
          v.insert(e, 0, mock(self.w, target_folder))
          v.end_edit(e)
          v.run_command("save")

  creator = DotensimeCreator(window)
  creator.do_create()

def edit(window):
  window.open_file(locations(window)[0])

def mock(window, root):
  """Creates a mock .ensime config for this particular window.
  Having a mock config is convenient for a user who doesn't know much
  about Ensime and needs some guidance from us.
  Return: a string with contents of a mock config.
  This function does not produce any side-effects (e.g. doesn't create files)"""

  # http://stackoverflow.com/questions/2504411/proper-indentation-for-python-multiline-strings
  def trim(docstring):
      if not docstring:
          return ''
      # Convert tabs to spaces (following the normal Python rules)
      # and split into a list of lines:
      lines = docstring.expandtabs().splitlines()
      # Determine minimum indentation (first line doesn't count):
      indent = sys.maxint
      for line in lines[1:]:
          stripped = line.lstrip()
          if stripped:
              indent = min(indent, len(line) - len(stripped))
      # Remove indentation (first line is special):
      trimmed = [lines[0].strip()]
      if indent < sys.maxint:
          for line in lines[1:]:
              trimmed.append(line[indent:].rstrip())
      # Strip off trailing and leading blank lines:
      while trimmed and not trimmed[-1]:
          trimmed.pop()
      while trimmed and not trimmed[0]:
          trimmed.pop(0)
      # Return a single string:
      return '\n'.join(trimmed)

  contents = """
    ;; This is a mock .ensime file created by the Ensime plugin.
    ;; It covers typical configuration entries necessary for an Ensime project.

    ;; Make sure that :sources contain only the folders that you need in your project,
    ;; and then fill in :compile-deps with a list of libraries your project depends on
    ;; (in .ensime lists are whitespace-separated, not comma-separated).

    ;; :target should point to the location that contains compiled classes for the project.
    ;; Ensime will use this location for completions and debugging.
    ;; However note that Ensime will not compile the project for you.
    ;; Use one of the established build tools (Ant, Maven, SBT, etc) to do that.

    ;; After that you can run Tools > Ensime > Maintenance > Startup
    ;; (this command, along with a few others, is also available via the command palette).

    ;; If your project contains a lot of files, it is advisable to enable :disable-source-load-on-startup t.
    ;; Otherwise Ensime might incur a massive lag at startup time.
    ;; At some point this scenario will be documented, but for now please contact us directly.
    ;; For Scala development use .ensime.SAMPLE from https://github.com/scala/scala.

    ;; For more information visit http://docs.sublimescala.org.
    ;; If something doesn't work, feel free to contact us at dev@sublimescala.org.

    (
      :root-dir "%s"
      :sources (
        $SOURCES
      )
      :compile-deps (
        ""
      )
      :target "%s"
    )
  """ % (root.replace("\\", "/"), root.replace("\\", "/"))
  contents = trim(contents)

  lines = contents.splitlines()
  iof = (i for i, line in enumerate(lines) if line.strip() == "$SOURCES").next()
  indent = " " * lines[iof].index("$")
  lines = lines[:iof] + map(lambda f: indent + "\"" + f.replace("\\", "/") + "\"", window.folders()) + lines[(iof + 1):]
  return '\n'.join(lines)

def select_subproject(conf, window, on_complete):
  """If more than one subproject is described in the given config sexp,
  prompt the user. Otherwise, return the sole subproject name."""
  m = sexp.sexp_to_key_map(conf)
  subprojects = [sexp.sexp_to_key_map(p) for p in m.get(":subprojects", [])]
  names = [p[":name"] for p in subprojects]
  if len(names) > 1:
    window.show_quick_panel(names, lambda i: on_complete(names[i]))
  elif len(names) == 1:
    sublime.set_timeout(functools.partial(on_complete, names[0]), 0)
  else:
    sublime.set_timeout(functools.partial(on_complete, None), 0)