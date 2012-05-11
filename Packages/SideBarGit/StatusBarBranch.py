import sublime, sublime_plugin
from sidebar.SideBarGit import SideBarGit
from sidebar.SideBarSelection import SideBarSelection
import threading
import os
import time

class Object():
	pass

s = sublime.load_settings('SideBarGit.sublime-settings')

class StatusBarBranch(sublime_plugin.EventListener):

	def on_load(self, v):
		file_name = self.effective_file_name(v)
		if s.get('statusbar_branch') and file_name:
			StatusBarBranchGet(file_name, v).start()

	def on_activated(self, v):
		file_name = self.effective_file_name(v)
		if s.get('statusbar_branch') and file_name:
			StatusBarBranchGet(file_name, v).start()

	def on_modified(self, v):
		file_name = self.effective_file_name(v)
		if s.get('statusbar_branch') and file_name != v.file_name() and v.name() != "Find Results":
			curr_time = time.time()
			last_time = self.last_time if hasattr(self, "last_time") else 0
			self.last_time = curr_time
			if curr_time - last_time > 5:
				print "launching git branch"
				StatusBarBranchGet(file_name, v).start()

	def effective_file_name(self, v):
    # how do I reliably detect currently open project?!
		project_root = v.settings().get("myke_project_root") or (v.window().folders()[0] if v.window() else None) if v else None
		current_file = (v.settings().get("myke_current_file") or v.file_name() if v else None) or None
		return current_file


class StatusBarBranchGet(threading.Thread):

	def __init__(self, file_name, v):
		threading.Thread.__init__(self)
		self.file_name = file_name
		self.v = v

	def run(self):
		for repo in SideBarGit().getSelectedRepos(SideBarSelection([self.file_name]).getSelectedItems()):
			object = Object()
			object.item = repo.repository
			object.command = ['git', 'branch']
			object.silent = True
			SideBarGit().run(object)
			sublime.set_timeout(lambda:self.on_done(SideBarGit.last_stdout.decode('utf-8')), 0)
			return

	def on_done(self, branches):
			branches = branches.split('\n')
			for branch in branches:
				if branch.startswith("*"):
					self.v.set_status('statusbar_sidebargit_branch', branch)
					return