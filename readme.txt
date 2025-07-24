Command for creating virtual environment
python -m venv venv
Command for Activating virtual environment
venv/Scripts/Activate.ps1
Command for Installing Dependencies 
pip install -r requirements.txt
Command for running file
python main.py

Note: If you see still red lines on import statments or terminal gives error that some dependencies are not installed it might that vscode is not configured  thus configure vscode to use the python executable in the virtual environment or venv folder. see image in the root to understand properly and make sure to activate the virtual environment before installing dependencies or running files.


Steps for using Tkinter GUI
1 Select the folder where your pdfs are located
2 Annotate each pdfs using the controls , drag mouse to create bounding boxes, right click to select a bounding box - you can resize it or delete it using delete key
3 Once done annotating all pdfs click on Save Annotations , Export to YOLO and COCO buttons.
4 Watch terminal output to check if the export was successful or not.
