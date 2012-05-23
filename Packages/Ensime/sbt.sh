#!/bin/bash
test -f ~/.sbtconfig && . ~/.sbtconfig
exec java -Xmx512M ${SBT_OPTS} -Dsbt.log.noformat=true -jar "$1/server/bin/sbt-launch-0.11.2.jar" "${@:2}"