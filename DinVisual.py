from PyQt5.QtCore import QThread, pyqtSlot, Qt
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QGridLayout, QProgressBar, QSizePolicy

from Serial.SerialWorker import SerialWorker


class DinVisual(QWidget):

    def __init__(self, imagedict, usbport=None, filelock=None, iccidpinfile=None, fw2data=None, fw3data=None):
        super().__init__()
        self.setMinimumSize(300, 400)
        self.imagedict = imagedict

        self.setupWidget()
        self.worker = SerialWorker(usbport, filelock, iccidpinfile, fw2data, fw3data)
        self.thread = QThread()

        self.worker.moveToThread(self.thread)

        self.worker.labelchangesig.connect(self.changeLabel)
        self.worker.progressupdatesig.connect(self.changePBar)
        self.worker.imagechangesig.connect(self.changeImage)

        self.thread.started.connect(self.worker.serialSetupLoop)
        self.thread.start()

    def setupWidget(self):
        layout = QGridLayout()
        self.setLayout(layout)

        self.labeldict = {
            "AUTH": QLabel(),
            "SN": QLabel(),
            "ICCID": QLabel(),
            "PIN": QLabel(),
            "FW": QLabel(),
            "AT": QLabel(),
            "STATUS": QLabel()
        }

        for label in self.labeldict.values():
            label.setAttribute(Qt.WA_TranslucentBackground)

        nestedlayout = QVBoxLayout()
        nestedlayout.addWidget(self.labeldict["AUTH"])
        nestedlayout.addWidget(self.labeldict["SN"])
        nestedlayout.addWidget(self.labeldict["ICCID"])
        nestedlayout.addWidget(self.labeldict["PIN"])
        nestedlayout.addWidget(self.labeldict["FW"])
        nestedlayout.addWidget(self.labeldict["AT"])

        self.imagehook = QLabel()
        self.imagehook.setPixmap(self.imagedict["DINDC"])
        self.imagehook.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        self.imagehook.setScaledContents(True)

        self.layout().addWidget(self.imagehook, 0, 0, 3, 3)
        self.layout()

        layout.addLayout(nestedlayout, 1, 1, 1, 1)

        self.layout().addWidget(self.labeldict["STATUS"], 3, 1, 1, 1)

        self.progressbar = QProgressBar()
        self.layout().addWidget(self.progressbar, 4, 0, 1, 3)

    @pyqtSlot(str, str)
    def changeLabel(self, labeltc, message):
        try:
            self.labeldict[labeltc].setText(message)
        except:
            pass

    @pyqtSlot(str)
    def changeImage(self, imagetc):
        try:
            self.imagehook.setPixmap(self.imagedict[imagetc])
        except:
            pass

    @pyqtSlot(int)
    def changePBar(self, value):
        try:
            self.progressbar.setValue(value)
        except:
            pass