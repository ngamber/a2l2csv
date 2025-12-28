import csv
import os
import sys
import io
import re
import logging
import threading
import time
import lib.Constants as Constants
from PyQt6.QtCore import QThread, pyqtSignal
from pya2l import DB
from lib.Constants import DBType


class LoadThread(QThread):
    logMessage = pyqtSignal(str)
    progressUpdate = pyqtSignal(int, str)  # (percentage, status_text)

    def __init__(self):
        super().__init__()

        self.db_type        = DBType.NONE
        self.a2ldb          = None
        self.a2lsession     = None
        self.csv_name_db    = {}
        self.csv_desc_db    = {}
        self.csv_address_db = {}
        self.filename       = ""
        self.forceRebuild   = False
        self._stop_monitoring = False
        self._monitor_thread = None
        
        # Set up logging handlers immediately upon thread creation
        # This ensures we catch ALL pya2l log messages
        self._setup_pya2l_logging()


    def _monitor_file_size(self, db_filename, a2l_file):
        """Monitor the database file size to estimate progress"""
        try:
            # Get the size of the source A2L file
            if os.path.exists(a2l_file):
                a2l_size = os.path.getsize(a2l_file)
            else:
                a2l_size = 1  # Avoid division by zero
            
            last_size = 0
            stall_count = 0
            
            while not self._stop_monitoring:
                time.sleep(0.5)  # Check every 500ms
                
                if os.path.exists(db_filename):
                    try:
                        current_size = os.path.getsize(db_filename)
                        
                        # Skip if file is too small (just created, not yet populated)
                        if current_size < 102400:  # Less than 100KB
                            continue
                        
                        # Estimate progress based on file size
                        estimated_final_size = a2l_size * 1.0
                        progress_ratio = min(current_size / estimated_final_size, 0.95)
                        progress = int(progress_ratio * 100)
                        
                        if current_size != last_size:
                            size_kb = current_size // 1024
                            self.progressUpdate.emit(progress, f"Building database... ({size_kb} KB)")
                            last_size = current_size
                            stall_count = 0
                        else:
                            stall_count += 1
                            if stall_count > 10:
                                break
                    except OSError:
                        time.sleep(0.1)
                        continue
                            
        except Exception as e:
            print(f"[FileMonitor] Error: {e}", flush=True)

    def _parse_progress_output(self, line):
        """Parse progress information from pya2l console output"""
        # Look for tqdm-style progress bars
        tqdm_match = re.search(r'(\d+)%\|', line)
        if tqdm_match:
            percentage = int(tqdm_match.group(1))
            self.progressUpdate.emit(percentage, "Importing A2L file...")
            return True
        
        # Try to match simple percentage format
        percent_match = re.search(r'(\d+)%', line)
        if percent_match:
            percentage = int(percent_match.group(1))
            self.progressUpdate.emit(percentage, "Processing...")
            return True
        
        # Look for specific pya2l messages
        if "Preprocessing" in line or "preprocessing" in line:
            self.progressUpdate.emit(30, "Preprocessing A2L file...")
            return True
        elif "Parsing" in line or "parsing" in line:
            self.progressUpdate.emit(60, "Parsing A2L structure...")
            return True
        elif "Creating database" in line or "Populating" in line:
            self.progressUpdate.emit(85, "Creating database...")
            return True
        
        return False
    
    def _setup_pya2l_logging(self):
        """Setup logging to capture pya2l progress messages"""
        # Remove any existing handlers first to avoid duplicates
        for logger_name in ['preprocessor', 'a2l', 'pya2l']:
            logger = logging.getLogger(logger_name)
            logger.handlers.clear()
        
        class ProgressHandler(logging.Handler):
            def __init__(self, thread):
                super().__init__()
                self.thread = thread
                self.setLevel(logging.INFO)
                
            def emit(self, record):
                try:
                    msg = record.getMessage()
                    sys.stdout.flush()
                    
                    # Parse pya2l log messages to update progress
                    if "Preprocessing and tokenizing" in msg:
                        self.thread.progressUpdate.emit(20, "Preprocessing A2L file...")
                    elif "Start parsing" in msg:
                        self.thread.progressUpdate.emit(50, "Parsing A2L structure...")
                    elif "Elapsed Time" in msg:
                        if "parsing" in msg.lower():
                            self.thread.progressUpdate.emit(70, "Parsing complete...")
                        else:
                            self.thread.progressUpdate.emit(40, "Preprocessing complete...")
                    elif "Number of keywords" in msg:
                        self.thread.progressUpdate.emit(90, "Finalizing database...")
                except Exception:
                    pass
        
        # Get pya2l loggers and add our handler
        handler = ProgressHandler(self)
        for logger_name in ['preprocessor', 'a2l', 'pya2l']:
            logger = logging.getLogger(logger_name)
            logger.setLevel(logging.INFO)
            logger.addHandler(handler)

    def run(self):
        self.logMessage.emit(f"Loading file: {self.filename}")
        self.progressUpdate.emit(0, "Starting...")

        self.a2ldb          = None
        self.a2lsession     = None
        self.csv_name_db    = {}
        self.csv_desc_db    = {}
        self.csv_address_db = {}

        # Ensure logging handlers are active
        for logger_name in ['preprocessor', 'a2l', 'pya2l']:
            logger = logging.getLogger(logger_name)
            if not logger.handlers:
                self._setup_pya2l_logging()
                break

        try:
            file_extension = self.filename.split(".")[-1]

            if file_extension.lower() == "csv":
                self._loadCSV()

            else:
                self._loadA2L()

        except Exception as e:
            self.logMessage.emit(f"Failed to load: {e}")
            self.progressUpdate.emit(0, "Error")


    def _loadA2L(self):
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

        except:
            self.logMessage.emit(f"Wait for database to build - {self.filename}")

            self.a2lsession = (
                self.a2ldb.import_a2l(self.filename, encoding="latin-1")
            )

        self.db_type = DBType.A2L
        self.logMessage.emit(f"Finished")


    def _loadCSV(self):
        with open(self.filename, "r", encoding="latin-1", newline='') as csvfile:
            csvreader = csv.DictReader(csvfile)

            for column_str in Constants.LIST_DATA_COLUMNS_REQUIRED:
                if column_str not in csvreader.fieldnames:
                    self.logMessage.emit(f"Failed to load: does not contain {column_str}")
                    return

            for row in csvreader:
                self.csv_name_db[row["Name"]] = {
                    "Name"          : row["Name"],
                    "Unit"          : row["Unit"],
                    "Equation"      : row["Equation"],
                    "Format"        : row["Format"],
                    "Address"       : row["Address"],
                    "Length"        : row["Length"],
                    "Signed"        : row["Signed"],
                    "ProgMin"       : row["ProgMin"],
                    "ProgMax"       : row["ProgMax"],
                    "WarnMin"       : row["WarnMin"],
                    "WarnMax"       : row["WarnMax"],
                    "Smoothing"     : row["Smoothing"],
                    "Enabled"       : row["Enabled"],
                    "Tabs"          : row["Tabs"],
                    "Assign To"     : row["Assign To"],
                    "Description"   : row["Description"] if "Description" in row else "",
                }

                if "Description" in row:
                    self.csv_desc_db[row["Description"]] = {
                        "Name"          : row["Name"],
                        "Unit"          : row["Unit"],
                        "Equation"      : row["Equation"],
                        "Format"        : row["Format"],
                        "Address"       : row["Address"],
                        "Length"        : row["Length"],
                        "Signed"        : row["Signed"],
                        "ProgMin"       : row["ProgMin"],
                        "ProgMax"       : row["ProgMax"],
                        "WarnMin"       : row["WarnMin"],
                        "WarnMax"       : row["WarnMax"],
                        "Smoothing"     : row["Smoothing"],
                        "Enabled"       : row["Enabled"],
                        "Tabs"          : row["Tabs"],
                        "Assign To"     : row["Assign To"],
                        "Description"   : row["Description"] if "Description" in row else "",
                    }

                self.csv_address_db[row["Address"]] = {
                    "Name"          : row["Name"],
                    "Unit"          : row["Unit"],
                    "Equation"      : row["Equation"],
                    "Format"        : row["Format"],
                    "Address"       : row["Address"],
                    "Length"        : row["Length"],
                    "Signed"        : row["Signed"],
                    "ProgMin"       : row["ProgMin"],
                    "ProgMax"       : row["ProgMax"],
                    "WarnMin"       : row["WarnMin"],
                    "WarnMax"       : row["WarnMax"],
                    "Smoothing"     : row["Smoothing"],
                    "Enabled"       : row["Enabled"],
                    "Tabs"          : row["Tabs"],
                    "Assign To"     : row["Assign To"],
                    "Description"   : row["Description"] if "Description" in row else "",
                }

            self.db_type = DBType.CSV
            self.logMessage.emit(f"Finished loading {len(self.csv_name_db)} items")