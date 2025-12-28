from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QFileDialog, QLineEdit, QLabel, QCheckBox
from lib.LoadThread import LoadThread
from lib.ReplaceThread import ReplaceThread
from lib.Constants import DBType

class TABDatabase(QWidget):
    def __init__(self, parent: QWidget):
        super().__init__(parent)
        self.parent     = parent

        #Load
        self.loadThread = LoadThread()
        self.loadThread.logMessage.connect(self.parent.addLogEntry)
        self.loadThread.finished.connect(self.onFinishedLoading)

        self.replaceThread = ReplaceThread(self.parent.addLogEntry, self.parent.getListItem, self.parent.updateListItem, self._replaceFinished)

        #Main layout box
        self.mainLayoutBox = QVBoxLayout()
        
        #Filename layout box
        self.fileNameLayoutBox = QHBoxLayout()
        self.fileLabel = QLabel()
        self.fileLabel.setFixedHeight(30)
        self.fileLabel.setText("Filename")
        self.fileNameLayoutBox.addWidget(self.fileLabel)

        self.fileEditBox = QLineEdit()
        self.fileEditBox.setFixedHeight(30)
        self.fileNameLayoutBox.addWidget(self.fileEditBox)

        self.findPushButton = QPushButton("Find")
        self.findPushButton.setFixedHeight(30)
        self.findPushButton.pressed.connect(self.FindButtonClick)
        self.fileNameLayoutBox.addWidget(self.findPushButton)

        self.mainLayoutBox.addLayout(self.fileNameLayoutBox)

        #Overwrite checkbox
        self.overwriteCheckBox = QCheckBox("Overwrite existing PID addresses")
        self.overwriteCheckBox.setChecked(False)
        self.mainLayoutBox.addWidget(self.overwriteCheckBox)

        #Load button
        self.loadPushButton = QPushButton("Load")
        self.loadPushButton.setFixedHeight(50)
        self.loadPushButton.pressed.connect(self.LoadButtonClick)
        self.mainLayoutBox.addWidget(self.loadPushButton)

        self.setLayout(self.mainLayoutBox)

        self._checkOverwrite()


    def FindButtonClick(self):
        dbFileName = QFileDialog.getOpenFileName(self, "Open Database", "", "Database (*.a2l *.a2ldb *.csv)",)
        self.fileEditBox.setText(dbFileName[0])


    def LoadButtonClick(self):
        self.loadPushButton.setEnabled(False)
        self.parent.tabs.setTabEnabled(1, False)
        self.parent.tabs.setTabEnabled(2, False)

        self.loadThread.filename = self.fileEditBox.text()
        self.loadThread.start()


    def onFinishedLoading(self):
        #overwrite list pid addresses
        if self.overwriteCheckBox.isChecked():
            self.replaceThread.newDBType              = self.loadThread.db_type
            self.replaceThread.newA2LSession          = self.loadThread.a2lsession
            self.replaceThread.newCSVNameDB           = self.loadThread.csv_name_db
            self.replaceThread.newCSVAddressDB        = self.loadThread.csv_address_db

            self.replaceThread.originalDBType         = self.parent.db_type
            self.replaceThread.originalA2LSession     = self.parent.a2lsession
            self.replaceThread.originalCSVNameDB      = self.parent.csv_name_db
            self.replaceThread.originalCSVAddressDB   = self.parent.csv_address_db

            self.replaceThread.run()

        else:
            self._loadDatabase()


    def _checkOverwrite(self):
        self.overwriteCheckBox.setEnabled(True if self.parent.db_type != DBType.NONE else False)


    def _loadDatabase(self):
        self.parent.a2ldb           = self.loadThread.a2ldb
        self.parent.a2lsession      = self.loadThread.a2lsession
        self.parent.csv_name_db     = self.loadThread.csv_name_db
        self.parent.csv_desc_db     = self.loadThread.csv_desc_db
        self.parent.csv_address_db  = self.loadThread.csv_address_db

        self.parent.db_type = self.loadThread.db_type

        #update layout
        self.loadPushButton.setEnabled(True)
        self._checkOverwrite()

        # Switch to Search tab if file loaded successfully
        if self.parent.db_type != DBType.NONE:
            self.parent.tabs.setTabEnabled(1, True)
            self.parent.tabs.setTabEnabled(2, True)
            self.parent.tabs.setCurrentIndex(1)
            
            # Check if there's a pending CSV file to load
            if hasattr(self.parent, 'checkAndLoadPendingCSV'):
                self.parent.checkAndLoadPendingCSV()


    def _replaceFinished(self):
        self._loadDatabase()