@REM add pyinstaller into dev group

@REM poetry add --group dev pyinstaller
@REM poetry install



@REM pyinstaller --onefile --hidden-import utils ./../meeting_summarizer/main_window.py
@REM pyinstaller  ./../meeting_summarizer/main_window.spec
pyinstaller --clean  ./../meeting_summarizer/main_window.spec
