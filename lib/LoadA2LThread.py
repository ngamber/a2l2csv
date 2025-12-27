import subprocess
import sys
import os
import lib.Constants as Constants
from PyQt6.QtCore import QThread, pyqtSignal
from pya2l import DB

class LoadA2LThread(QThread):
    logMessage = pyqtSignal(str)

    def __init__(self):
        super().__init__()

        self.a2ldb      = None
        self.a2lsession = None
        self.filename   = ""


    def run(self):
        self.logMessage.emit(f"Loading file: {self.filename}")

        self.a2ldb = DB()

        try:
            self.a2lsession = (
                self.a2ldb.open_existing(self.filename)
            )
            
            # Apply SQLite performance optimizations
            # These pragmas improve query performance on all platforms (Windows, macOS, Linux)
            if Constants.APPLY_SQL_OPTIMIZATIONS:
                try:
                    self.a2lsession.execute("PRAGMA journal_mode=WAL")
                    self.a2lsession.execute("PRAGMA synchronous=NORMAL")
                    self.a2lsession.execute("PRAGMA cache_size=-64000")  # 64MB cache
                    self.a2lsession.execute("PRAGMA temp_store=MEMORY")
                    self.a2lsession.commit()
                except Exception as e:
                    # If pragmas fail, log but continue - database will still work
                    self.logMessage.emit(f"Note: Could not apply SQLite optimizations: {e}")

            self.logMessage.emit("Database loaded")

        except:
            try:
                self.logMessage.emit(f"Wait for database to build - {self.filename}")
                
                # Check if running as PyInstaller executable
                if getattr(sys, 'frozen', False):
                    # Running as PyInstaller exe - build database directly in thread
                    # This avoids the subprocess issue where sys.executable points to the .exe
                    self.a2lsession = self.a2ldb.import_a2l(self.filename, encoding="latin-1")
                else:
                    # Running as Python script - use subprocess to avoid blocking
                    command = [
                        sys.executable,         # Path to the Python executable
                        "lib/Build_a2ldb.py",   # The script to run
                        self.filename,          # Filename
                    ]
                    
                    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    stdout, stderr = process.communicate()
                    
                    if process.returncode != 0:
                        error_msg = stderr.decode() if stderr else "Unknown error"
                        raise Exception(f"Database build failed: {error_msg}")
                    
                    # Open the newly created database
                    self.a2lsession = self.a2ldb.open_existing(self.filename)
                
                self.logMessage.emit(f"Finished")

            except Exception as e:
                self.logMessage.emit(f"Failed to load: {e}")