@echo off
setlocal enabledelayedexpansion

:: Loop through all JSON files in the current directory
for %%F in (*.json) do (
    set "filename=%%~nF"
    echo { > "%%F"
    echo.    "parent": "minecraft:item/generated", >> "%%F"
    echo.    "textures": { >> "%%F"
    echo.        "layer0": "lom:item/gui/npcs/hearts/!filename!" >> "%%F"
    echo.    } >> "%%F"
    echo } >> "%%F"
)

echo All JSON files have been overridden.
pause
/O          List by files in sorted order.
  sortorder    N  By name (alphabetic)       S  By size (smallest first)
               E  By extension (alphabetic)  D  By date/time (oldest first)
               G  Group directories first    -  Prefix to reverse order