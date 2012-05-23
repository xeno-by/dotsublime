@ECHO OFF
set SCRIPT_DIR=%~dp0
java -Xmx512M %SBT_OPTS% -Dsbt.log.noformat=true -jar "%SCRIPT_DIR%\server\bin\sbt-launch-0.11.2.jar" %*