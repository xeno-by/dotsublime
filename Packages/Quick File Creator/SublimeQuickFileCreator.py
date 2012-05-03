import os
import re
import sublime
import sublime_plugin


class QuickCreateFileCreatorBase(sublime_plugin.WindowCommand):
    def doCommand(self):
        if not self.find_roots():
            return

        self.construct_excluded_pattern()
        self.init_relative_paths()
        for root in self.roots:
            self.build_relative_paths(root)
        self.move_current_directory_to_top()
        self.window.show_quick_panel(self.relative_paths, self.dir_selected)

    def find_roots(self):
        folders = self.window.folders()
        if len(folders) == 0:
            sublime.error_message('Could not find project roots')
            return False

        self.roots = folders
        return True

    def find_dir_root(self, dir):
        for folder in self.window.folders():
            if dir.startswith(folder):
                return folder
            rel_path_start = folder.rindex("\\") + 1
            alias = folder[rel_path_start:]
            if dir.startswith(alias):
                return folder
        return ""

    def construct_excluded_pattern(self):
        patterns = [pat.replace('|', '\\') for pat in self.get_setting('excluded_dir_patterns')]
        self.excluded = re.compile('^(?:' + '|'.join(patterns) + ')$')

    def get_setting(self, key):
        settings = None
        view = self.window.active_view()

        if view:
            settings = self.window.active_view().settings()

        if settings and settings.has('SublimeQuickFileCreator') and key in settings.get('SublimeQuickFileCreator'):
            # Get project-specific setting
            results = settings.get('SublimeQuickFileCreator')[key]
        else:
            # Get user-specific or default setting
            settings = sublime.load_settings('SublimeQuickFileCreator.sublime-settings')
            results = settings.get(key)
        return results

    def init_relative_paths(self):
        self.relative_paths = []

    def build_relative_paths(self, root):
        rel_path_start = root.rindex("\\") + 1
        relative_path = root[rel_path_start:]
        self.relative_paths.append(relative_path)

        for base, dirs, files in os.walk(root):
            dirs_copy = dirs[:]
            [dirs.remove(dir) for dir in dirs_copy if self.excluded.search(dir)]

            for dir in dirs:
                relative_path = os.path.join(base, dir)[rel_path_start:]
                self.relative_paths.append(relative_path)

    def move_current_directory_to_top(self):
        view = self.window.active_view()

        if view:
            file_dir = os.path.dirname(view.file_name())
            file_root = self.find_dir_root(file_dir)
            rel_path_start = file_root.rindex("\\") + 1
            cur_dir = file_dir[rel_path_start:]
            for path in self.relative_paths:
                if path == cur_dir:
                    i = self.relative_paths.index(path)
                    self.relative_paths.insert(0, self.relative_paths.pop(i))
                    break

    def dir_selected(self, selected_index):
        if selected_index != -1:
            self.selected_dir = self.relative_paths[selected_index]
            self.window.show_input_panel(self.INPUT_PANEL_CAPTION, '', self.file_name_input, None, None)

    def file_name_input(self, file_name):
        dir = self.selected_dir

        dir_root = self.find_dir_root(dir)
        dir_root = dir_root[:dir_root.rindex("\\")]
        full_path = os.path.join(dir_root, dir, file_name)
        if os.path.lexists(full_path):
            sublime.error_message('File already exists:\n%s' % full_path)
            return
        else:
            self.create_and_open_file(full_path)


class QuickCreateFileCommand(QuickCreateFileCreatorBase):
    INPUT_PANEL_CAPTION = 'File name:'

    def run(self):
        self.doCommand()

    def create_and_open_file(self, path):
        open(path, 'w')
        self.window.open_file(path)


class QuickCreateDirectoryCommand(QuickCreateFileCreatorBase):
    INPUT_PANEL_CAPTION = 'Folder name:'

    def run(self):
        self.doCommand()

    def create_and_open_file(self, path):
        os.mkdir(path)
