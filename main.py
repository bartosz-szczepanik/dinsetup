import sys
from math import floor
from threading import Lock
from PyQt5.QtCore import Qt

#from configdialog import ConfigDialog

from PyQt5.QtWidgets import QApplication, QMainWindow, QGridLayout, QAction, qApp, QWidget, \
    QTabWidget
from PyQt5.QtGui import QKeySequence, QPixmap

#from dinworker import DinSerialWorker
from TCP.ConfigTcpDialog import ConfigTcpDialog
from Widgets.DinVisual import DinVisual
from Serial.configdialog import ConfigDialog


class MainWindowLayout(QWidget):

    def __init__(self):
        super(MainWindowLayout, self).__init__()
        self.setUpdatesEnabled(True)
        self.setLayout(QGridLayout())
        self.tabs = QTabWidget()
        self.serialtab = QWidget()
        self.tcptab = QWidget()
        self.serialtab.setLayout(QGridLayout())

        self.tabs.addTab(self.serialtab, "Serial")
        self.tabs.addTab(self.tcptab, "TCP")
        self.layout().addWidget(self.tabs)

        self.imagedict = {
            "DINDC": QPixmap("resources/images/dinicon/dinicondc.png"),
            "DINCN": QPixmap("resources/images/dinicon/diniconlive.png"),
            "DINPIN": QPixmap("resources/images/dinicon/diniconpin.png"),
            "DINFW": QPixmap("resources/images/dinicon/diniconfw.png"),
            "DINFIN": QPixmap("resources/images/dinicon/dinicondone.png")
        }

    def updateamount(self, selected, pincsvfile, fw2data, fw3data, configdata):#, pincsvfile, fwv2datafile, fwv3datafile, fwv2filename, fwv3filename):
        filelock = Lock()
        try:
            f = open("karton_piatek_38sztuk.txt", "r")
        except:
            f = open("karton_piatek_38sztuk.txt", "w")
        f.close()
        for i in reversed(range(self.serialtab.layout().count())):
            #self.serialtab.layout().itemAt(i).widget().close()
            self.serialtab.layout().itemAt(i).widget().setParent(None)
        amount = len(selected)
        for number in range(0, amount):
            usbport = selected[number].split(" ")[1]
            test = DinVisual(self.imagedict, usbport, filelock, pincsvfile, fw2data, fw3data, configdata)
            self.serialtab.layout().addWidget(test, floor(number/4), number%4)
            self.serialtab.update()
        self.update()



class App(QMainWindow):

    def __init__(self):
        super(App, self).__init__()
        self.setUpdatesEnabled(True)
        self.title = 'DM'
        self.initUI()

    def initUI(self):
        self.setWindowTitle(self.title)
        self.setWindowFlags( Qt.WindowCloseButtonHint | Qt.WindowMaximizeButtonHint)
        geometry = qApp.desktop().availableGeometry(self)
        self.frameGeometry().setCoords(200, 200, geometry.width() * 0.5, geometry.height() * 0.7)



        self.menu = self.menuBar()
        self.file_menu = self.menu.addMenu("File")

        exit_action = QAction("Exit", self)
        exit_action.setShortcut(QKeySequence.Quit)
        exit_action.triggered.connect(self.close)

        self.file_menu.addAction(exit_action)

        config_action = QAction("Config", self)
        config_action.setShortcut(QKeySequence.Quit)
        config_action.triggered.connect(self.toolbarConfigClick)

        self.file_menu.addAction(config_action)

        self.status = self.statusBar()
        self.status.showMessage("App Loaded")

        self.mainwindow = MainWindowLayout()
        self.setCentralWidget(self.mainwindow)
        self.setStyleSheet(open("resources/stylesheet.css").read())


        self.show()
    def toolbarConfigClick(self):
        if self.mainwindow.tabs.currentIndex() == 0:
            dialog = ConfigDialog()
            if dialog.exec_():
                if len(dialog.result):
                    self.mainwindow.updateamount(dialog.result, dialog.pincsvfile, dialog.fwv2datafile, dialog.fwv3datafile, dialog.configdata)
                    self.update()
            else:
                pass
        else:
            dialog = ConfigTcpDialog()
            if dialog.exec_():
                if len(dialog.result):
                    self.mainwindow.updateamount(dialog.result, dialog.pincsvfile, dialog.fwv2datafile, dialog.fwv3datafile)
                    self.update()
            else:
                pass


if __name__ == '__main__':
    sys._excepthook = sys.excepthook

    def exception_hook(exctype, value, traceback):
        sys._excepthook(exctype, value, traceback)
        sys.exit(1)

    sys.excepthook = exception_hook

    app = QApplication(sys.argv)
    ex = App()
    try:
        sys.exit(app.exec_())
    except Exception as e:
        print(e)
