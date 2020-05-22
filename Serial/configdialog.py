from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QDialog, QDialogButtonBox, QVBoxLayout, QListWidget, QInputDialog, QAbstractItemView, \
    QGridLayout, QPushButton, QFileDialog
from xlrd import open_workbook
import serial.tools.list_ports
import glob

class ConfigDialog(QDialog):

    def __init__(self, *args, **kwargs):
        super(ConfigDialog, self).__init__(*args, **kwargs)
        self.setStyleSheet(open("resources/stylesheet.css").read())
        self.setWindowTitle("ConfigSerial")
        self.result = []
        self.pincsvfile = None
        self.fwv2datafile = None
        self.fwv3datafile = None
        self.fwv2filename = None
        self.fwv3filename = None
        self.configdata = None

        QBtn = QDialogButtonBox.Ok | QDialogButtonBox.Cancel

        self.buttonBox = QDialogButtonBox(QBtn)
        self.buttonBox.accepted.connect(self.okbuttonhandler)
        self.buttonBox.rejected.connect(self.reject)


        self.activeusblist = QListWidget()
        self.activeusblist.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.activeusblist.itemSelectionChanged.connect(self.getCurrentSelection)
        self.populateList()

        self.pincsvfilebttn = QPushButton("PINFILE")
        self.pincsvfilebttn.clicked.connect(self.pinCsvDialog)

        self.fwv2bttn = QPushButton("FWv2")
        self.fwv2bttn.clicked.connect(self.fwV2Dialog)

        self.fwv3bttn = QPushButton("FWv3")
        self.fwv3bttn.clicked.connect(self.fwV3Dialog)

        self.refreshbutton = QPushButton()
        self.refreshbutton.setIcon(QIcon("resources/images/icons/refreshicon.png"))
        self.refreshbutton.clicked.connect(self.populateList)

        self.configbutton = QPushButton("CONFIG")
        self.configbutton.clicked.connect(self.configDialog)

        self.layout = QGridLayout()
        self.layout.addWidget(self.pincsvfilebttn, 0, 0)
        self.layout.addWidget(self.fwv2bttn, 1, 0)
        self.layout.addWidget(self.fwv3bttn, 2, 0)
        self.layout.addWidget(self.activeusblist, 0, 1, 3, 3)
        self.layout.addWidget(self.buttonBox, 3, 3)
        self.layout.addWidget(self.configbutton,3,0)
        self.layout.addWidget(self.refreshbutton, 3, 2)
        self.setLayout(self.layout)

    def okbuttonhandler(self):
        try:
            if not self.pincsvfile:
                self.pincsvfile = self.findPinFile()
            if not self.fwv2datafile:
                self.fwv2datafile = self.findDefaultFw("v2")
            if not self.fwv3datafile:
                self.fwv2datafile = self.findDefaultFw("v3")
            if not self.configdata:
                self.configdata = self.findDefaultConfig()
        except:
            self.result = []
        self.accept()

    def findDefaultFw(self,version):
        fw = glob.glob("resources/fw/"+version+"/*default*")
        return open(fw[0],"rb").read()

    def findDefaultConfig(self):
        config = glob.glob("resources/configs/*default*")
        return open(config[0],"rb").read()

    def findPinFile(self):
        pinfile = glob.glob("resources/pins/*default*")
        return open_workbook(pinfile[0]).sheet_by_index(0)

    def populateList(self):
        self.activeusblist.clear()
        for tmp in serial.tools.list_ports.comports():
            try:
                self.activeusblist.addItem(tmp.device+" "+tmp.location)
            except:
                pass

    def getCurrentSelection(self):
        self.result = [i.text() for i in self.activeusblist.selectedItems()]

    def configDialog(self):
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        fileName, _ = QFileDialog.getOpenFileName(self,"QFileDialog.getOpenFileName()", "","All Files (*);;Python Files (*.py)", options=options)#stop: 0 #1ad780, stop: 1 #7fdbb1
        if fileName:
            self.configdata = open(fileName, "rb").read()
            self.configbutton.setStyleSheet("background-color: QLinearGradient( x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 #bcff8a, stop: 0.1 #1ad780, stop: 0.5 #1ad780, stop: 0.9 #7fdbb1, stop: 1 #6d805e);"
                                        "color: #3b3b3b;")


    def pinCsvDialog(self):
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        fileName, _ = QFileDialog.getOpenFileName(self,"QFileDialog.getOpenFileName()", "","All Files (*);;Python Files (*.py)", options=options)#stop: 0 #1ad780, stop: 1 #7fdbb1
        if fileName:
            wb = open_workbook(fileName)
            self.pincsvfile = wb.sheet_by_index(0)
            #self.pincsvfile = {}
            self.pincsvfilebttn.setStyleSheet("background-color: QLinearGradient( x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 #bcff8a, stop: 0.1 #1ad780, stop: 0.5 #1ad780, stop: 0.9 #7fdbb1, stop: 1 #6d805e);"
                                        "color: #3b3b3b;")
        else:
            self.pincsvfile = None

    def fwV2Dialog(self):
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        fileName, _ = QFileDialog.getOpenFileName(self,"QFileDialog.getOpenFileName()", "","All Files (*);;Python Files (*.py)", options=options)
        if fileName:
            tmp = open(fileName, "rb")
            self.fwv2datafile = tmp.read()
            self.fwv2filename = tmp.name
            self.fwv2bttn.setStyleSheet("background-color: QLinearGradient( x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 #bcff8a, stop: 0.1 #1ad780, stop: 0.5 #1ad780, stop: 0.9 #7fdbb1, stop: 1 #6d805e);"
                                        "color: #3b3b3b;")
    def fwV3Dialog(self):
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        fileName, _ = QFileDialog.getOpenFileName(self,"QFileDialog.getOpenFileName()", "","All Files (*);;Python Files (*.py)", options=options)
        if fileName:
            tmp = open(fileName,"rb")
            self.fwv3datafile = tmp.read()
            self.fwv3filename = tmp.name
            self.fwv3bttn.setStyleSheet("background-color: QLinearGradient( x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 #bcff8a, stop: 0.1 #1ad780, stop: 0.5 #1ad780, stop: 0.9 #7fdbb1, stop: 1 #6d805e);"
                                        "color: #3b3b3b;")
