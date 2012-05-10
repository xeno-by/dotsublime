import sublime, sublime_plugin
import subprocess
import os
from _winreg import *

class MykeGitMenu(sublime_plugin.WindowCommand):
  def run(self):
    # how do I reliably detect currently open project?!
    view = self.window.active_view()
    self.project_root = (view.settings().get("myke_project_root") if view else None) or self.window.folders()[0]
    self.current_file = (view.settings().get("myke_current_file") or view.file_name() if view else None) or self.project_root
    self.current_dir = view.settings().get("myke_current_file") or view.file_name() if view else None
    self.current_dir = os.path.dirname(self.current_dir) if self.current_dir else self.project_root

    menu = ["1. Checkout", "2. New branch", "3. Rename branch", "4. Delete branch", "5. Merge", "6. Rebase", "7. Cherry-pick", "8. Reset hard", "9. Reset mixed", "a. Navigate branches", "q. Navigate commits"]
    self.window.show_quick_panel(menu, self.command_selected)

  def command_selected(self, selected_index):
    if selected_index == 0:
      incantation = "myke /S smart-list-branches"
      print("Running " + incantation + " at " + self.current_dir)
      p = subprocess.Popen(incantation, shell = True, stdout = subprocess.PIPE, cwd = self.current_dir)
      output, _ = p.communicate()
      self.menu = output.split('\r\n')[:-1]
      index = (i for i,v in enumerate(self.menu) if v.startswith("* ")).next()
      self.window.show_quick_panel(self.menu, self.checkout, 0, index)
    elif selected_index == 1:
      incantation = "myke /S smart-list-branches"
      print("Running " + incantation + " at " + self.current_dir)
      p = subprocess.Popen(incantation, shell = True, stdout = subprocess.PIPE, cwd = self.current_dir)
      output, _ = p.communicate()
      self.menu = output.split('\r\n')[:-1]
      index = (i for i,v in enumerate(self.menu) if v.startswith("* ")).next()
      self.window.show_quick_panel(self.menu, self.new_branch, 0, index)
    elif selected_index == 2:
      incantation = "myke /S smart-list-branches"
      print("Running " + incantation + " at " + self.current_dir)
      p = subprocess.Popen(incantation, shell = True, stdout = subprocess.PIPE, cwd = self.current_dir)
      output, _ = p.communicate()
      self.menu = output.split('\r\n')[:-1]
      index = (i for i,v in enumerate(self.menu) if v.startswith("* ")).next()
      self.window.show_quick_panel(self.menu, self.rename_branch, 0, index)
    elif selected_index == 3:
      incantation = "myke /S smart-list-branches"
      print("Running " + incantation + " at " + self.current_dir)
      p = subprocess.Popen(incantation, shell = True, stdout = subprocess.PIPE, cwd = self.current_dir)
      output, _ = p.communicate()
      self.menu = output.split('\r\n')[:-1]
      index = (i for i,v in enumerate(self.menu) if v.startswith("* ")).next()
      self.window.show_quick_panel(self.menu, self.delete_branch, 0, index)
    elif selected_index == 4:
      incantation = "myke /S smart-list-branches"
      print("Running " + incantation + " at " + self.current_dir)
      p = subprocess.Popen(incantation, shell = True, stdout = subprocess.PIPE, cwd = self.current_dir)
      output, _ = p.communicate()
      self.menu = output.split('\r\n')[:-1]
      index = (i for i,v in enumerate(self.menu) if v.startswith("* ")).next()
      self.window.show_quick_panel(self.menu, self.merge, 0, index)
    elif selected_index == 5:
      incantation = "myke /S smart-list-branches"
      print("Running " + incantation + " at " + self.current_dir)
      p = subprocess.Popen(incantation, shell = True, stdout = subprocess.PIPE, cwd = self.current_dir)
      output, _ = p.communicate()
      self.menu = output.split('\r\n')[:-1]
      index = (i for i,v in enumerate(self.menu) if v.startswith("* ")).next()
      self.window.show_quick_panel(self.menu, self.rebase, 0, index)
    elif selected_index == 6:
      incantation = "myke /S smart-list-commits"
      print("Running " + incantation + " at " + self.current_dir)
      p = subprocess.Popen(incantation, shell = True, stdout = subprocess.PIPE, cwd = self.current_dir)
      output, _ = p.communicate()
      self.menu = output.split('\r\n')[:-1]
      index = (i for i,v in enumerate(self.menu) if v.startswith("* ")).next()
      self.window.show_quick_panel(self.menu, self.cherry_pick, 0, index)
    elif selected_index == 7:
      incantation = "myke /S smart-list-branch-commits"
      print("Running " + incantation + " at " + self.current_dir)
      p = subprocess.Popen(incantation, shell = True, stdout = subprocess.PIPE, cwd = self.current_dir)
      output, _ = p.communicate()
      self.menu = output.split('\r\n')[:-1]
      index = (i for i,v in enumerate(self.menu) if v.startswith("* ")).next()
      self.window.show_quick_panel(self.menu, self.reset_hard, 0, index)
    elif selected_index == 8:
      incantation = "myke /S smart-list-branch-commits"
      print("Running " + incantation + " at " + self.current_dir)
      p = subprocess.Popen(incantation, shell = True, stdout = subprocess.PIPE, cwd = self.current_dir)
      output, _ = p.communicate()
      self.menu = output.split('\r\n')[:-1]
      index = (i for i,v in enumerate(self.menu) if v.startswith("* ")).next()
      self.window.show_quick_panel(self.menu, self.reset_mixed, 0, index)
    elif selected_index == 9:
      incantation = "myke /S smart-list-branches"
      print("Running " + incantation + " at " + self.current_dir)
      p = subprocess.Popen(incantation, shell = True, stdout = subprocess.PIPE, cwd = self.current_dir)
      output, _ = p.communicate()
      self.menu = output.split('\r\n')[:-1]
      index = (i for i,v in enumerate(self.menu) if v.startswith("* ")).next()
      self.window.show_quick_panel(self.menu, self.navigate_branches, 0, index)
    elif selected_index == 10:
      incantation = "myke /S smart-list-commits"
      print("Running " + incantation + " at " + self.current_dir)
      p = subprocess.Popen(incantation, shell = True, stdout = subprocess.PIPE, cwd = self.current_dir)
      output, _ = p.communicate()
      self.menu = output.split('\r\n')[:-1]
      index = (i for i,v in enumerate(self.menu) if v.startswith("* ")).next()
      self.window.show_quick_panel(self.menu, self.navigate_commits, 0, index)

  def get_selection(self, selected_index):
    raw = self.menu[selected_index]
    if raw.startswith("* "):
      raw = raw[2:]
    self.selection = raw
    return self.selection

  def checkout(self, selected_index):
    if selected_index == -1:
      return
    self.window.run_command("myke", {"cmd": "smart-checkout", "args": [self.get_selection(selected_index)]})

  def new_branch(self, selected_index):
    if selected_index == -1:
      return
    self.window.show_input_panel("New branch name:", self.get_selection(selected_index), self.new_branch_input, None, None)

  def new_branch_input(self, name):
    self.window.run_command("myke", {"cmd": "smart-branch-new-select", "args": [self.selection, name]})

  def rename_branch(self, selected_index):
    if selected_index == -1:
      return
    self.window.show_input_panel("New branch name:", self.get_selection(selected_index), self.rename_branch_input, None, None)

  def rename_branch_input(self, name):
    self.window.run_command("myke", {"cmd": "smart-branch-rename", "args": [self.selection, name]})

  def delete_branch(self, selected_index):
    if selected_index == -1:
      return
    self.window.show_quick_panel(["Yes, delete branch " + self.get_selection(selected_index), "No, do not delete"], self.delete_branch_confirmed)

  def delete_branch_confirmed(self, selected_index):
    if selected_index == 0:
      self.window.run_command("myke", {"cmd": "smart-branch-remote-delete", "args": [self.selection]})

  def merge(self, selected_index):
    if selected_index == -1:
      return
    self.window.run_command("myke", {"cmd": "smart-merge", "args": [self.get_selection(selected_index)]})

  def rebase(self, selected_index):
    if selected_index == -1:
      return
    self.window.run_command("myke", {"cmd": "smart-rebase", "args": [self.get_selection(selected_index)]})

  def cherry_pick(self, selected_index):
    if selected_index == -1:
      return
    self.window.run_command("myke", {"cmd": "smart-cherry-pick", "args": [self.get_selection(selected_index)]})

  def reset_hard(self, selected_index):
    if selected_index == -1:
      return
    self.window.show_quick_panel(["Yes, reset hard up to " + self.get_selection(selected_index), "No, do not reset"], self.reset_hard_confirmed)

  def reset_hard_confirmed(self, selected_index):
    if selected_index == 0:
      self.window.run_command("myke", {"cmd": "smart-hard-reset", "args": [self.selection]})

  def reset_mixed(self, selected_index):
    if selected_index == -1:
      return
    self.window.show_quick_panel(["Yes, reset mixed up to " + self.get_selection(selected_index), "No, do not reset"], self.reset_mixed_confirmed)

  def reset_mixed_confirmed(self, selected_index):
    if selected_index == 0:
      self.window.run_command("myke", {"cmd": "smart-mixed-reset", "args": [self.selection]})

  def navigate_branches(self, selected_index):
    if selected_index == -1:
      return
    self.window.run_command("myke", {"cmd": "smart-list-branch-commits", "args": [self.get_selection(selected_index)]})

  def navigate_commits(self, selected_index):
    if selected_index == -1:
      return
    self.window.run_command("myke", {"cmd": "smart-show-commit", "args": [self.get_selection(selected_index)]})
