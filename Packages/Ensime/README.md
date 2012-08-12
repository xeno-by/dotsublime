# Sublime ENSIME

This project provides integration with ENSIME and Sublime Text Editor 2.
It's a fork of the original sublime-ensime project, written by Ivan Porto Carrero.
This fork introduces stability improvements, user-friendly setup and error messages,
better logging and works with the latest pre-release version of Scala 2.10.

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

The first release will include go to definition (aka ctrl+click) and on-the-fly error highlighting.
We'd also love to add debugging facilities at some point in the future.

## How to install?

1. Install the package itself:

    In your Sublime Text `Packages` dir (you can find it by `Preferences > Browse Packages`), invoke:

    ```
    git clone git://github.com/sublimescala/sublime-ensime.git Ensime
    ```

2. Install Ensime.

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