import sys
import argparse
import os
import lib.Constants as Constants
from PyQt6.QtWidgets import QMainWindow, QApplication, QWidget, QVBoxLayout, QListWidget, QTabWidget
from pya2l import DB, model
from pya2l.api import inspect
from lib.TABA2L import TABA2L
from lib.TABSearch import TABSearch
from lib.TABList import TABList


class MainWindow(QMainWindow):
    def __init__(self, a2l_file=None):
        super().__init__()

        #Variables used to hold a2l database
        self.a2ldb      = DB()
        self.a2lsession = None

        #set title
        self.setWindowTitle(Constants.APPLICATION_VERSION_STRING)

        #tabs
        self.listTab = TABList(self)
        self.a2lTab = TABA2L(self)

        self.tabs = QTabWidget()
        self.tabs.addTab(self.a2lTab, "A2L")
        self.tabs.addTab(TABSearch(self), "Search")
        self.tabs.addTab(self.listTab, "List")

        #log box
        self.listViewLog = QListWidget()
        self.listViewLog.setFixedHeight(100)
        layoutLog = QVBoxLayout()
        layoutLog.addWidget(self.listViewLog)

        layoutBoxAll = QVBoxLayout()
        layoutBoxAll.addWidget(self.tabs)
        layoutBoxAll.addLayout(layoutLog)

        widget = QWidget()
        widget.setLayout(layoutBoxAll)
        self.setGeometry(300, 300, 650, 600)
        self.setCentralWidget(widget)
        self.show()

        # Auto-load A2L file if provided
        if a2l_file:
            self.load_a2l_file(a2l_file)


    def addLogEntry(self, entry):
        self.listViewLog.addItem(entry)
        self.listViewLog.scrollToBottom()


    def addListItem(self, item, overwrite=False):
        self.listTab.addListItem(item, overwrite)

    def load_a2l_file(self, filepath):
        """Load an A2L file programmatically"""
        if os.path.exists(filepath):
            self.addLogEntry(f"Auto-loading A2L file: {filepath}")
            self.a2lTab.fileEditBox.setText(filepath)
            self.a2lTab.LoadButtonClick()
        else:
            self.addLogEntry(f"Error: A2L file not found: {filepath}")


# Main
def main():
    parser = argparse.ArgumentParser(
        description='A2L to CSV converter - GUI tool for working with A2L files',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  %(prog)s                    Launch GUI without loading a file
  %(prog)s myfile.a2l         Launch GUI and auto-load myfile.a2l
  %(prog)s /path/to/file.a2l  Launch GUI and auto-load file from path
        '''
    )
    parser.add_argument(
        'a2l_file',
        nargs='?',
        help='Optional A2L file to load on startup'
    )
    
    # Parse only known args to allow Qt to handle its own arguments
    args, unknown = parser.parse_known_args()
    
    # Validate A2L file if provided
    if args.a2l_file:
        if not os.path.exists(args.a2l_file):
            print(f"Error: A2L file not found: {args.a2l_file}")
            sys.exit(1)
        if not args.a2l_file.lower().endswith(('.a2l', '.a2ldb')):
            print(f"Warning: File does not have .a2l or .a2ldb extension: {args.a2l_file}")
    
    # Create Qt application with remaining arguments
    app = QApplication([sys.argv[0]] + unknown)
    w = MainWindow(a2l_file=args.a2l_file)
    sys.exit(app.exec())


if __name__ == '__main__':
    main()