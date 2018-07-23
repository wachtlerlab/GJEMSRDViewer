# GJEMSRDViewer
pyQT4 based gui application for viewing electrophysiological traces of Ginjang Project

## Installation
Create a virtual environment with conda/pyenv/pipenv and install the packages in "setup.py" within it.
Activate the environment and you are good to go!

## Running the GUI
Either run the application using `python <path to GJEMSRDViewer.py>`

or

Create a standalone application using PyInstaller as:

`pyinstaller GJEMSRDViewer.py`

Then navigate into the folder ".../GJEMSRawDataViewer/dist/GJEMSRDViewer/" and execute "GJEMSRDViewer" or "GJEMSRDViewer.exe"

## Using the GUI
1. Select an SMR file on file system in the field "SMR File"
2. (optional) If the experiment that generated the SMR file had a voltage calibration string in the excel file ("neuron_database.xlsx"), enter it in the field "Voltage Calibration Entry"
3. (optional) If the experiment that generated the SMR file had a "Interval to Exclude (s)" entry in the excel file ("neuron_database.xlsx"), enter it in the field "Intervals to Exclude Entry"
4. Load the file with the key F4 or from File->Load Data
5. To view a specific interval of time, enter the start and end times of this interval in the fields "Start time in s" and "End Time in s" and refresh the plot using F5 or File -> Refresh Plot.
6. The buttons "Next" and "Previous" can be used to refresh the plot to the time intervals following and preceeding the current plot. The time iterval of the plot remains the same.






