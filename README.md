# EDLCopy

## Description
Qt Python App

Usage: Film Production/Post Production 

Copy Camera Raw Footages From Source to Destination  

Input Txt Files OR EDL Files

Use rsync OS Command to execute copy

Use Thread
## Release Date
2023 02 10 

## Steps
### 1
Create and cd a folder for your work: Ex. /User/gump/EDLCopy
### 2 
conda create -n qtapp --python=3.19
### 3
conda activate qtapp
### 4
pip install pyinstaller

pip install PyQt5
### 5
Download UI Designer

https://build-system.fman.io/qt-designer-download

Qt Designer.dmg
### 6
Using Qt Designer to create UI

Then Export layout.ui to layout.py by

pyuic5 layout.ui -o layout.py

### 7
When you finish your coding, put a logo.ico into your folder 

then pack into an app by

pyinstaller --windowed --onefile --icon=logo.ico --clean --noconfirm gump_EDLCopy.py  -n EDLCopy

### 8
inside the dist folder are your app. 

Two files: one with logo, the other will open the console.


