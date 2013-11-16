import sublime, sublime_plugin
import os, json
from subprocess import Popen, call, PIPE
from urllib.request import urlopen
import re

class MyGithubComment(sublime_plugin.TextCommand):
  def run(self, edit):
    self.w = self.view.window()
    self.v = self.view
    self.f = self.view.file_name()
    if not self.f: return

    full_name = os.path.realpath(self.f)
    folder_name, _ = os.path.split(full_name)
    git_root = Popen([os.environ["SHELL"], "-c", "git-root"], cwd=folder_name, stdout=PIPE).communicate()[0].decode()[:-1]
    curr_relative_name = full_name[len(git_root)+1:]
    curr_line_number = self.view.rowcol(self.view.sel()[0].begin())[0] + 1

    incantation = "git blame -L" + str(curr_line_number) + ",+1 -p \"" + full_name + "\" | head -n 1 | cut -d' ' -f1 -f2"
    sha, prev_line_number = Popen([os.environ["SHELL"], "-c", incantation], cwd=git_root, stdout=PIPE).communicate()[0].decode()[:-1].split(" ")
    incantation = "git blame -L" + str(curr_line_number) + ",+1 \"" + full_name + "\" | cut -d' ' -f2"
    prev_relative_name = Popen([os.environ["SHELL"], "-c", incantation], cwd=git_root, stdout=PIPE).communicate()[0].decode()[:-1]
    incantation = "hub-introspect"
    user, repo, _, _ = Popen([os.environ["SHELL"], "-c", incantation], cwd=git_root, stdout=PIPE).communicate()[0].decode()[:-1].split("\n")
    incantation = "git show --name-only " + sha
    diff_files = Popen([os.environ["SHELL"], "-c", incantation], cwd=git_root, stdout=PIPE).communicate()[0].decode()[:-1].split("\n")
    diff_files = diff_files[(len(diff_files) - 1) - diff_files[::-1].index("")+1:]
    # print(diff_files)
    file_id = "diff-" + str(diff_files.index(prev_relative_name))

    # TODO: no idea what's the purpose of ids that come after "diff-" in urls like the following
    # view-source:https://github.com/xeno-by/dotsublime/commit/e30cb9ba851f05d0ca8df6a993714299ae5c0794#diff-733841a6a6ee6dfcaf59536c44894ee7L180
    # therefore I have to infer them by loading a web page and trying to figure out real IDs from it
    # api_url = "https://api.github.com/repos/" + user + "/" + repo + "/commits?sha=" + sha + "&page=1&per_page=1"
    # api_url = "https://api.github.com/repos/" + user + "/" + repo + "/commits/" + sha
    web_url = "https://github.com/" + user + "/" + repo + "/commit/" + sha
    content = urlopen(web_url).read().decode("utf-8")
    index = content.index("<div id=\"" + file_id)
    fragment = content[0:index][-100:]
    file_ghid = re.search(r"(diff-[0123456789abcdefABCDEF]+)", fragment).groups()[0]
    web_url += "#" + file_ghid + "R" + str(prev_line_number)
    import webbrowser
    webbrowser.open(web_url)

  # TODO: copy/pasted from MyGaika.py. how do I remove duplication?
  def detect_project_root(self):
    def try_project_root(path):
      if path:
        if "sandbox" in path:
          return os.path.abspath(path + "/..")
        if os.path.exists(os.path.join(path, "sandbox")):
          return path
        if os.path.exists(os.path.join(path, "project")):
          return path
        parent = os.path.dirname(path)
        if parent != path:
          return try_project_root(parent)

    try:
      maybe_root = try_project_root(self.f)
      if maybe_root: return maybe_root

      project = self.w.project_file_name()
      folders = json.load(open(project))["folders"]
      for folder in folders:
        maybe_root = try_project_root(folder["path"])
        if maybe_root: return maybe_root
    except Exception as ex:
      print(ex)
      pass
