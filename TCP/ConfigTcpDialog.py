from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QDialog, QDialogButtonBox, QVBoxLayout, QListWidget, QInputDialog, QAbstractItemView, \
    QGridLayout, QPushButton, QFileDialog
from xlrd import open_workbook
import serial.tools.list_ports

class ConfigTcpDialog(QDialog):

    def __init__(self, *args, **kwargs):
        super(ConfigTcpDialog, self).__init__(*args, **kwargs)
        self.setStyleSheet(open("../stylesheet.css").read())
        self.setWindowTitle("ConfigTcp")
        self.result = []
        self.pincsvfile = None
        self.fwv2datafile = None
        self.fwv3datafile = None
        self.fwv2filename = None
        self.fwv3filename = None

        QBtn = QDialogButtonBox.Ok | QDialogButtonBox.Cancel

        self.buttonBox = QDialogButtonBox(QBtn)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

        self.pincsvfilebttn = QPushButton("DeviceList")
        self.pincsvfilebttn.clicked.connect(self.pinCsvDialog)

        self.fwv2bttn = QPushButton("FWv2")
        self.fwv2bttn.clicked.connect(self.fwV2Dialog)

        self.fwv3bttn = QPushButton("FWv3")
        self.fwv3bttn.clicked.connect(self.fwV3Dialog)

        self.refreshbutton = QPushButton()
        self.refreshbutton.setIcon(QIcon("../images/icons/refreshicon.png"))
        self.refreshbutton.clicked.connect(self.populateList)

        self.layout = QGridLayout()
        self.layout.addWidget(self.pincsvfilebttn, 0, 0)
        self.layout.addWidget(self.fwv2bttn, 1, 0)
        self.layout.addWidget(self.fwv3bttn, 2, 0)
        self.layout.addWidget(self.buttonBox, 3, 0)
        self.setLayout(self.layout)

    def populateList(self):
        self.activeusblist.clear()
        for tmp in serial.tools.list_ports.comports():
            try:
                self.activeusblist.addItem(tmp.device+" "+tmp.location)
            except:
                pass

    def getCurrentSelection(self):
        self.result = [i.text() for i in self.activeusblist.selectedItems()]

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
