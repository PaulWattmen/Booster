from PyQt5.QtCore import QThread

class SyncWorker(QThread):
    """Worker to sync monday database with local database"""

    def __init__(self, synchronizer,parent=None):
        """Constructor
        :param synchronizer: MondaySynchronizer object to synchronize with
        :type synchronizer: MondaySynchronizer"""
        super(SyncWorker, self).__init__(parent)
        self.synchronizer = synchronizer

    def run(self):
        self.synchronizer.sync()
