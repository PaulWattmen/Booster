# -*- coding: utf-8 -*-

from PyQt5.QtCore import Qt
import os
import math
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
from .Plot_ViewWindow.plot_dialog import PlotDialog
import json


class PlotWindow():
    """QGIS window to add plots to monday."""

    def __init__(self,layer_name):
        """constructor"""
        self.dlg = PlotDialog()
        if os.name == "nt":  # if running on windows
            self.dlg.setWindowFlags(Qt.WindowStaysOnTopHint)
        self.selected_plot = None
        self.plot_infos = {}
        layer_list = QgsProject.instance().mapLayersByName(layer_name)
        if layer_list:
            self.layer = layer_list[0]
            self.layer.selectionChanged.connect(self.on_plot_selected)
        else:
            self.layer = None



    def on_plot_selected(self):
        """This method is called whenever a new plot is selected by the user.
                Store and display the attributes of the selected plot"""
        if self.layer.selectedFeatureCount():
            selected_features = self.layer.selectedFeatures()
            self.selected_plot = selected_features[0]
            self.get_attributes()

    def shorten_geometry(self,coordinates_list, wanted_length):
        i = 0
        shortened_list = []
        mod = math.floor(len(coordinates_list)/wanted_length) +1
        print(f'mod : {mod}')
        for coords in coordinates_list:
            if i%mod ==0:
                shortened_list.append(coords)
            i+=1
        return shortened_list


    def get_attributes(self):
        """display the selected plots attributes in the log widget"""
        if self.selected_plot:
            self.plot_infos["idu"] = self.selected_plot["idu"]
            self.plot_infos["Surface"] = str(self.selected_plot["Contenance"])
            self.plot_infos["Code Postal"] = str(self.selected_plot["code_insee"])
            self.plot_infos["Département"] = str(self.selected_plot["code_dep"])
            self.plot_infos["Commune"] = self.selected_plot["nom_com"]
            self.plot_infos["Géometrie"] = json.loads(self.selected_plot.geometry().asJson())
            wanted_length = 60
            print("longueur avant traitement : " + str(len(self.plot_infos["Géometrie"]["coordinates"][0][0])))
            if len(self.plot_infos["Géometrie"]["coordinates"][0][0])>wanted_length:
                self.plot_infos["Géometrie"]["coordinates"][0][0] = self.shorten_geometry(self.plot_infos["Géometrie"]["coordinates"][0][0], wanted_length)
                print("longueur après traitement : " +str(len(self.plot_infos["Géometrie"]["coordinates"][0][0])))

            self.writeLog(
            f""" - idu : {self.selected_plot["idu"]}
         - Surface : {self.selected_plot["Contenance"]}
         - Code Postal : {self.selected_plot["code_insee"]}
         - Département : {self.selected_plot["code_dep"]}
         - Commune : {self.selected_plot["nom_com"]}
        """)

    def writeLog(self,text):
        """Overwrite a message into the log widget
            :params text: the string to display
            :type text: str"""
        self.dlg.plot_log.setText(text)

    def appendLog(self,text):
        """Append a message into the log widget
            :params text: the string to display
            :type text: str"""
        a_text = self.dlg.log.toPlainText() + '\n'
        self.dlg.plot_log.setText(a_text+text)



