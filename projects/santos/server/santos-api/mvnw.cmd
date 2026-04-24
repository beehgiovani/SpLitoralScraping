@REM ----------------------------------------------------------------------------
@REM Maven Wrapper startup script for Windows
@REM ----------------------------------------------------------------------------

@IF "%DEBUG%" == "on" @ECHO ON
@SETLOCAL

@REM Find the project root
@SET "basedir=%~dp0"
@IF "%basedir:~-1%"=="\" SET "basedir=%basedir:~0,-1%"

@REM Configuration
@SET "MAVEN_PROJECT_JAR=%basedir%\.mvn\wrapper\maven-wrapper.jar"
@SET "WRAPPER_PROPERTIES=%basedir%\.mvn\wrapper\maven-wrapper.properties"

@REM Download the jar if it doesn't exist
@IF NOT EXIST "%MAVEN_PROJECT_JAR%" (
    @FOR /F "tokens=1,2 delims==" %%A IN ('findstr "wrapperUrl" "%WRAPPER_PROPERTIES%"') DO @SET "WRAPPER_URL=%%B"
    @ECHO Downloading Maven Wrapper jar...
    @powershell -Command "& { [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; $webClient = New-Object System.Net.WebClient; $webClient.DownloadFile('%WRAPPER_URL%', '%MAVEN_PROJECT_JAR%') }"
)

@REM Find Java
@SET "JAVACMD=java"
@IF NOT "%JAVA_HOME%" == "" SET "JAVACMD=%JAVA_HOME%\bin\java.exe"

@REM Run Maven
@"%JAVACMD%" ^
  -classpath "%MAVEN_PROJECT_JAR%" ^
  "-Dmaven.multiModuleProjectDirectory=%basedir%" ^
  org.apache.maven.wrapper.MavenWrapperMain ^
  %*

@ENDLOCAL
