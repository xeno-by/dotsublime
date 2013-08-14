import sublime, sublime_plugin
import re, os

class MyDoubleClick(sublime_plugin.TextCommand):
  def run(self, edit):
    v = self.view
    sel = v.sel()
    def seek(rx_key, immediate):
      rx = v.settings().get(rx_key)
      if rx:
        def loop(point, first_iter):
          if point < 0: return None
          l = v.line(point)
          m = re.search(rx, v.substr(l))
          if m:
            return m
          else:
            if immediate: return None
            else: return loop(l.a - 1, first_iter = False)
        return loop(sel[0].a, first_iter = True)
    def match(rx_key):
      return (seek(rx_key, immediate = False), seek(rx_key, immediate = True))
    (fm, fimm), (lm, limm) = match("result_file_regex"), match("result_line_regex")
    if fm and (fimm or limm):
      def substr_and_fixup(begin, end):
        text = v.substr(sublime.Region(begin, end))
        # compatibility with how iTerm2 passes strings to semantic history handlers
        return text.replace("(", "\(").replace(")", "\)").replace(" ", "\ ").replace("\n", "\ ")
      file_name = fm.groups()[0]
      line_number = lm.groups()[0] if lm else fm.groups()[1]
      before_click = substr_and_fixup(v.line(sel[0]).a, sel[0].a)
      after_click = substr_and_fixup(sel[0].a, v.line(sel[0]).b)
      view_dir = os.path.basename(v.file_name()) if v.file_name() else None
      cwd = v.settings().get("result_base_dir") or view_dir or ""
      os.spawnlp(os.P_NOWAIT, "click-through", "click-through", file_name, line_number, before_click, after_click, cwd)
    else:
      sel.add(v.word(sel[0]))
