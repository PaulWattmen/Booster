# -*- coding: utf-8 -*-

from qgis.PyQt.QtCore import QSettings, QTranslator, QCoreApplication,QTextCodec
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction
from qgis.utils import iface
from qgis.core import (
    QgsProject,
    QgsVectorLayer,
    QgsField,
    QgsFeature,
    QgsGeometry,
    QgsExpression,
    QgsFeatureRequest,
    QgsJsonUtils
)


# Import the code for the dialog
from .EditingWindow.edition_dialog import EditionDialog
import os.path
import json
from pathlib import Path


class EditionWindow():
    """QGIS Window to edit plot data."""

    def __init__(self, monday_parameters, plot_infos):
        """Constructor
        :param monday_parameters: dic containing the options labels of the multichoice columns
        :param plot_infos: dic of keys/values attributes of the plot"""

        self.monday_parameters = monday_parameters
        self.plot_infos = plot_infos
        self.dlg = EditionDialog()
        self.init_combo_box()
        self.fill_fields()



    def init_combo_box(self):
        self.dlg.etat.addItems([status for status in self.monday_parameters["status_list"]])
        self.dlg.techno.addItems([brique_tek for brique_tek in self.monday_parameters["techno_list"]])
    def fill_fields(self):

        self.dlg.plot_label.setText(self.plot_infos["idu"])
        if self.plot_infos["Qualité"]:
            self.dlg.qualite.setValue(int(self.plot_infos["Qualité"]))
        self.dlg.etat.setCurrentText(self.plot_infos["Etat"])
        print(self.plot_infos["Brique Techno"])
        self.dlg.techno.setCurrentText(str(self.plot_infos["Brique Techno"]))

