& 'C:\Qt\6.6.1\msvc2019_64\bin\rcc.exe' -g python -compress 2 -threshold 30 resources.qrc -o resources.py
(Get-Content resources.py -Raw) -replace 'from PySide6 import QtCore', 'from PyQt6 import QtCore' | Set-Content resources.py