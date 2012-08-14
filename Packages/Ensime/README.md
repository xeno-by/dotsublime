# Sublime ENSIME

This project provides integration with ENSIME and Sublime Text Editor 2.
It's a fork of the original sublime-ensime project, written by Ivan Porto Carrero.
This fork introduces additional features, stability improvements, user-friendly setup and error messages,
better logging. It also works with the latest pre-release version of Scala 2.10.

Sublime ENSIME strives to realize the dream of having Scala semantic services
inside a lightning fast and feature-rich text editor. Big thanks to Aemon Cannon,
Daniel Spiewak and Ivan Porto Carrero who demonstrated that this vision is possible
and inspired us to kick off the project.

## Project status

This is a beta version. Basic things will work (for example, error highlighting),
but there might still be problems. Please, submit issues to our tracker
if you catch SublimeScala misbehaving: https://github.com/sublimescala/sublime-ensime/issues/new.

Also note that SublimeScala uses a pre-release Scala compiler (which roughly corresponds to 2.10.0-M6).
This might also produce funny bugs. Use our bug reporting facility to report those:
https://issues.scala-lang.org/secure/CreateIssue!default.jspa.

Anyways this venture is very important for the project maintainers, since we use Scala every day,
so we'll do our best to do a polished release around the time of the final release of Scala 2.10.0.

## Features

* Creates and understands `.ensime` projects (maximum one project per Sublime window,
  if you have a project with multiple subprojects only a single subproject will be available at a time)

* Once your Ensime project is configured (we have a helper for that) and Ensime is run,
  Scala files in that Ensime project benefit from a number of semantic services:

    * On-the-fly typechecking and error highlighting on save. Error messages are displayed
      in the status bar when you click highlighted regions (unfortunately, Sublime Text 2 doesn't
      support programmable tooltips). Moreover, errors can be viewed in a dynamically updated buffer
      displayed with `Tools > Ensime > Commands > Show notes`.

    * Type-aware completions for identifiers (integrates into the built-in mechanism of completions
      in Sublime Text 2, depending on your configuration it might be bound to `Ctrl+Space` or `Tab`)

    * Type-aware go to definition (implemented by `ensime_go_to_definition` command: bind it yourself
      to your favorite hotkey or uncomment an entry in the provided mousemap to bind to `Ctrl+Click`)

* Implements prototype support for debugging. At the moment you can set breakpoints, create launch
  configurations and step through programs in the debugger. This is a very early prototype,
  so it's unlikely that you'll be able to do anything useful with it, however it does illustrate
  future development directions for this plugin

* Hosts ENSIME in a completely transparent fashion. Solves the problem of runaway processes
  on Windows (Linux and Mac is on to-do list, we also wouldn't mind pull requests)

* Tested on sources of scalac on Windows and Ubuntu (using ENSIME v0.9.6.5 with embedded Scala 2.10.0-M6)

## How to install?

1. Install the package itself:

    a. (Not yet available, [coming soon](https://github.com/wbond/package_control_channel/pull/514))
    If you use [Package Control](http://wbond.net/sublime_packages/package_control), install package Ensime.
    (`Preferences > Package Control > Install Package > Ensime`).

    b. In your Sublime Text `Packages` dir (you can find it by `Preferences > Browse Packages`), invoke:

    ```
    git clone git://github.com/sublimescala/sublime-ensime.git Ensime
    ```

2. Install the ENSIME server:

    Download Ensime from http://download.sublimescala.org.
    The archive will contain a directory with an Ensime version.

    Extract the contents of this directory into the `server` subdirectory
    of just created `sublime-ensime` directory. If you do everything correctly,
    `sublime-ensime/server/bin` will contain Ensime startup scripts and
    `sublime-ensime/server/lib` will contain Ensime binaries.

3. (Re)start Sublime Text editor.

4. Configure Ensime.

    a. Use `Preferences > Package Settings > Ensime` to customize
       different aspects of this plugin.

    b. If you want to use Ctrl+Click for `Go to Definition`,
       invoke `Preferences > Package Settings > Mousemap - Default`
       and either uncomment the relevant entry or copy it to your custom mousemap.
       (Warning: this is an experimental feature, it might work incorrectly
       with other Sublime plugins).

## How to use?

Open the Sublime command palette (typically bound to `Ctrl+Shift+P`) and type `Ensime: Startup`.

If you don't have an Ensime project, the plugin will guide you through creating it.

If you already have a project, an ENSIME server process will be started in the background,
and the server will initialize a resident instance of the Scala compiler.
After the server is ready, a message will appear in the left-hand corner of the status bar.
It will read either `ENSIME` if the currently opened file belongs to the active Ensime project
or `ensime` if it doesn't. Keep an eye on this message - it's an indicator of things going well.

## Contacts

In case if something goes wrong, let us know at dev@sublimescala.org or
submit an issue to the tracker https://github.com/sublimescala/sublime-ensime/issues/new.
Regards, the SublimeScala team.