# MASPY-GUI
Interface for the Visual Representation and Debugging of the [MASPY Framework](https://github.com/laca-is/MASPY)

## Installation
To install the interface [MASPY-GUI](https://pypi.org/project/maspy-gui/)

	pip install maspy-gui 
## Update
	pip install maspy-gui -U
## Tutorial
0. Choose a MASPY implementation to add the interface
   
1.	Import the interface
```python
from gui.start import start_interface
```
2.	Add in the first line of your main:
```python
def main():
Admin(listener_log=True)
```
3. Comment your start_system() and add start_interface()
```python
#Admin().start_system()
start_interface()
```


