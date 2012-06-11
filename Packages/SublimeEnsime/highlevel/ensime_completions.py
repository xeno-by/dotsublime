class EnsimeCompletionsListener(sublime_plugin.EventListener):
  def on_query_completions(self, view, prefix, locations):
    if not view.match_selector(locations[0], "source.scala"):
      return []
    completions = EnsimeApi(view).complete_member(view.file_name(), locations[0])
    if completions is None:
      return []
    return ([(c.name + "\t" + c.signature, c.name) for c in completions], sublime.INHIBIT_EXPLICIT_COMPLETIONS | sublime.INHIBIT_WORD_COMPLETIONS)

