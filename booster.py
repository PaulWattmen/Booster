# -*- coding: utf-8 -*-
"""
/***************************************************************************
 Booster
                                 A QGIS plugin
 This plugin allows to sync the monday database with the qgis data visualization
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                              -------------------
        begin                : 2024-11-06
        git sha              : $Format:%H$
        copyright            : (C) 2024 by Paul Poissonnet - Wattmen
        email                : paul.poissonnet@wattmen.org
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
from qgis.PyQt.QtCore import QSettings, QTranslator, QCoreApplication,QTextCodec
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction
from qgis.utils import iface
from PyQt5.QtCore import Qt
from qgis.core import (
    QgsProject,
    QgsVectorLayer,
    QgsField,
    QgsFeature,
    QgsGeometry,
    QgsExpression,
    QgsMapLayer,
    QgsFeatureRequest,
    QgsWkbTypes,
    QgsJsonUtils,
)
from PyQt5.QtCore import QThread
from PyQt5.QtCore import QVariant

# Initialize Qt resources from file resources.py
from .resources import *
# Import the code for the dialog
from .booster_dialog import BoosterDialog
import os.path
import json
import time
from .python_files.MondaySynchronizer import MondaySynchronizer
from .python_files.PlotWindow import PlotWindow
from .python_files.EditionWindow import EditionWindow
from .python_files.ETEXFiller.EtexWindow import EtexWindow
from .python_files.SyncWorker import SyncWorker
from urllib.parse import urlencode
from pathlib import Path

import requests
import datetime


class Booster:
    """QGIS Plugin allowing to use Monday as a database for the plots acquisition projects."""

    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        # Save reference to the QGIS interface
        self.iface = iface
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'Booster_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)
            QCoreApplication.installTranslator(self.translator)

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&Booster')

        # Check if plugin was started the first time in current QGIS session
        # Must be set in initGui() to survive plugin reloads
        self.first_start = None
        self.synchronizer = None
        self.layer_name = "Parcelles - Monday"
        self.all_plot_layer_name = "Cadastre Parcellaire"
        self.plu_layer = None
        self.rpg_layer = None
        self.protected_layers = {"PROTECTEDAREAS.SIC:sic":None,
                                 "PROTECTEDAREAS.ZPS:zps":None,
                                 "PROTECTEDAREAS.ZNIEFF1:znieff1":None,
                                 "PROTECTEDAREAS.ZNIEFF2:znieff2":None}
        self.get_layer()
        self.selected_plot = None
        self.editionwindow = None
        self.etexwindow = None
        self.sync_worker = None
        # noinspection PyMethodMayBeStatic
    def tr(self, message):
        """Get the translation for a string using Qt translation API.

        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('Booster', message)


    def add_action(
        self,
        icon_path,
        text,
        callback,
        enabled_flag=True,
        add_to_menu=True,
        add_to_toolbar=True,
        status_tip=None,
        whats_this=None,
        parent=None):
        """Add a toolbar icon to the toolbar.

        :param icon_path: Path to the icon for this action. Can be a resource
            path (e.g. ':/plugins/foo/bar.png') or a normal file system path.
        :type icon_path: str

        :param text: Text that should be shown in menu items for this action.
        :type text: str

        :param callback: Function to be called when the action is triggered.
        :type callback: function

        :param enabled_flag: A flag indicating if the action should be enabled
            by default. Defaults to True.
        :type enabled_flag: bool

        :param add_to_menu: Flag indicating whether the action should also
            be added to the menu. Defaults to True.
        :type add_to_menu: bool

        :param add_to_toolbar: Flag indicating whether the action should also
            be added to the toolbar. Defaults to True.
        :type add_to_toolbar: bool

        :param status_tip: Optional text to show in a popup when mouse pointer
            hovers over the action.
        :type status_tip: str

        :param parent: Parent widget for the new action. Defaults None.
        :type parent: QWidget

        :param whats_this: Optional text to show in the status bar when the
            mouse pointer hovers over the action.

        :returns: The action that was created. Note that the action is also
            added to self.actions list.
        :rtype: QAction
        """

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            # Adds plugin icon to Plugins toolbar
            self.iface.addToolBarIcon(action)

        if add_to_menu:
            self.iface.addPluginToMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""


        icon_path = os.path.join(self.plugin_dir,"icon.png")
        self.add_action(
            icon_path,
            text=self.tr(u'Booster'),
            callback=self.run,
            parent=self.iface.mainWindow())

        # will be set False in run()
        self.first_start = True


    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&Booster'),
                action)
            self.iface.removeToolBarIcon(action)


    def run(self):
        """Run method that performs all the real work"""

        # Create the dialog with elements (after translation) and keep reference
        # Only create GUI ONCE in callback, so that it will only load when the plugin is started
        if self.first_start == True:
            self.synchronizer = MondaySynchronizer()
            self.first_start = False
            self.dlg = BoosterDialog()

            self.writeLog("Synchronisez pour obtenir les dernières modifications !")
            if os.path.isfile(os.path.join(self.synchronizer.relative_path, self.synchronizer.save_json_file_name)):
                self.appendLog(f'Dernière MàJ : {datetime.datetime.fromtimestamp(os.path.getmtime(os.path.join(self.synchronizer.relative_path, self.synchronizer.save_json_file_name)),tz=datetime.timezone(datetime.timedelta(hours=1)))}')


        # Connect actions to the buttons
            self.dlg.sync_pushButton.clicked.connect(self.sync)
            self.dlg.search_pushButton.clicked.connect(self.search_plot)
            self.dlg.edit_pushButton.clicked.connect(self.edit_plot)
            self.dlg.etex_pushButton.clicked.connect(self.launch_etex_prog)
            self.dlg.total_sync_pushButton.clicked.connect(
                lambda: self.synchronizer.load_all_data_from_monday())
            self.dlg.monday_pushButton.clicked.connect(lambda : self.synchronizer.open_in_browser(self.selected_plot["idu"]))
            self.dlg.maps_pushButton.clicked.connect(lambda: self.synchronizer.open_in_google_maps(self.selected_plot.geometry().asJson()))
            self.dlg.display_plot_checkBox.clicked.connect(self.load_wfs_layer_with_extent)
            self.dlg.display_plu_checkBox.clicked.connect(self.toggle_plu_display)
            self.dlg.display_rpg_checkBox.clicked.connect(self.toggle_rpg_display)
            self.dlg.display_protected_checkBox.clicked.connect(self.toggle_protected_display)
            self.dlg.rejected.connect(self.close)

        if os.name == "nt":  # if running on windows
            self.dlg.setWindowFlags(Qt.WindowStaysOnTopHint)
        self.set_side_position_for_dialogs(self.dlg)  # Move the window on the side of the screen
        self.dlg.show()
        # Run the dialog event loop
        result = self.dlg.exec_()


        if result:
            iface.edition_window = None
            if self.sync_worker:
                self.sync_worker.wait()
            # Do something useful here - delete the line containing pass and
            # substitute with your code.

    def set_side_position_for_dialogs(self,dialog,dy=0):
        """Move a window to the right side of the main qgis window so that it's not hiding the main interface

                :param dialog: The window to move
                :type dialog: qdialog
                :param dy: height offset in px
                """
        main_window = iface.mainWindow()
        geometry = main_window.geometry().center()


        x = main_window.x()+main_window.width()-dialog.width()*1.05
        y=dy+ geometry.y()-dialog.geometry().center().y()/2

        dialog.move(int(x),int(y))

    def sync(self):
        """Launch the parallel worker that reads the data from Monday"""
        if not self.synchronizer:
            self.synchronizer = MondaySynchronizer()
        self.writeLog("Synchronisation en cours...")
        self.sync_worker = SyncWorker(self.synchronizer)
        self.sync_worker.finished.connect(self.update_layer_on_thread_finished)
        self.sync_worker.start()

    def update_layer_on_thread_finished(self):
        """Update the monday plot layer in QGIS once the sync worker is done"""

        self.update_layer(self.layer_name, self.synchronizer.geojson_dict)
        self.writeLog("Synchronisation finie !")
        self.appendLog(
            f'Dernière MàJ : {datetime.datetime.fromtimestamp(os.path.getmtime(os.path.join(self.synchronizer.relative_path, self.synchronizer.save_json_file_name)), tz=datetime.timezone(datetime.timedelta(hours=1)))}')

        self.worker = None


    def update_layer(self, layer_name, data_dict):
        """Update/refresh a layer in QGIS.
            :param layer_name: The name of the layer to update
            :type layer_name: string
            :param data_dict: the dictionary containing attributes and geometry of the layer. Must be GeoJson format.
            :type data_dict:dict
        """
        self.delete_already_existing_layer(layer_name)

        #convert a dic into Qgis features
        fcString = json.dumps(data_dict)
        codec = QTextCodec.codecForName("UTF-8")
        fields = QgsJsonUtils.stringToFields(fcString, codec)
        feats = QgsJsonUtils.stringToFeatureList(fcString, fields, codec)

        vl = QgsVectorLayer('MultiPolygon', layer_name, "memory")
        dp = vl.dataProvider()
        dp.addAttributes(fields)
        vl.updateFields()

        dp.addFeatures(feats)
        vl.updateExtents()

        QgsProject.instance().addMapLayer(vl)

        #if the method is running for the main monday plot layer, apply appropriate style
        if layer_name == self.layer_name:
            stylefile_path = os.path.join(Path(__file__).parent,'qgis_style_files','plot_from_monday_style.qml')
            vl.loadNamedStyle(stylefile_path)

            self.get_layer()
            if self.layer: #enable elem count view
                layer_tree = iface.layerTreeView().layerTreeModel().rootGroup()

                # Find the layer's node in the layer tree
                layer_node = layer_tree.findLayer(self.layer)
                layer_node.setCustomProperty("showFeatureCount", True)

        # if the method is running for the complete plot database layer, apply appropriate style
        if layer_name == self.all_plot_layer_name:
            stylefile_path = os.path.join(Path(__file__).parent, 'qgis_style_files', 'classic_plot_style.qml')
            vl.loadNamedStyle(stylefile_path)

    def get_layer(self):
        """Store the main layer instance and listen for new selections"""
        layer_list = QgsProject.instance().mapLayersByName(self.layer_name)
        if layer_list:
            self.layer = layer_list[0]
            self.layer.selectionChanged.connect(self.on_plot_selected)
        else:
            self.layer = None

    def on_plot_selected(self):
        """This method is called whenever a new plot is selected by the user.
        Store the attributes of the selected plot"""
        if self.layer.selectedFeatureCount():
            selected_features = self.layer.selectedFeatures()
            self.selected_plot = selected_features[0]
            self.get_attributes()

    def edit_plot(self):
        """Open the edition window and send the selected plot infos to it.
             Needs a plot to be selected first"""
        if self.selected_plot:
            self.editionwindow = EditionWindow(self.synchronizer.parameters, self.selected_plot.attributeMap())
            self.editionwindow.dlg.send.clicked.connect(self.modify_monday_elem)
            self.editionwindow.dlg.delete_button.clicked.connect(self.delete_monday_elem)
            self.set_side_position_for_dialogs(self.editionwindow.dlg)
            self.editionwindow.dlg.show()

    def launch_etex_prog(self):
        if self.selected_plot:
            self.etexwindow = EtexWindow(self.selected_plot.attributeMap())
            self.set_side_position_for_dialogs(self.etexwindow.dlg)
            self.etexwindow.dlg.show()

    def modify_monday_elem(self):
        """Called when a edit is made from the edition window.
             Stick a new state, quality and technology to an already existing plot in monday"""
        plot_infos = {}
        plot_infos["idu"] = self.editionwindow.dlg.plot_label.text()
        plot_infos["Etat"] = self.editionwindow.dlg.etat.currentText()
        plot_infos["Brique techno"] = self.editionwindow.dlg.techno.currentText()
        plot_infos["Qualité"] = {"rating" : int(self.editionwindow.dlg.qualite.text())}
        self.editionwindow.dlg.done(0)
        self.synchronizer.modify_element_to_monday(plot_infos)
        self.update_layer(self.layer_name, self.synchronizer.geojson_dict)
        self.sync()

    def delete_monday_elem(self):
        """Called when the delete button is pressed from the edition window.
    delete an already existing element from Monday"""
        idu = self.editionwindow.dlg.plot_label.text()
        self.editionwindow.dlg.done(0)
        self.synchronizer.delete_element_in_monday(idu)
        self.update_layer(self.layer_name, self.synchronizer.geojson_dict)




    def search_plot(self):
        """Search a plot by its idu and zoom on it."""
        searched_idu = self.dlg.plot_id_lineEdit.text()
        filter_expression = f""""idu" LIKE '%{searched_idu}%'"""
        request = QgsFeatureRequest(QgsExpression(filter_expression))
        self.selected_plot = list(self.layer.getFeatures(request))[0]

        self.layer.selectByIds([self.selected_plot.id()])
        iface.actionZoomToSelected().trigger()
        self.get_attributes()


    def get_attributes(self):
        """get the attributes of the actual selected plot to display them in the log"""
        if self.selected_plot:
            self.writeLog("")
            table = self.selected_plot.attributeMap()
            for elem in table.items():
                self.appendLog(f'{elem[0]} : {elem[1]}')



    def load_wfs_layer_with_extent(self):
        """Display the window to upload new plots to monday and
        show all the plots existing in the user's view window"""

        if self.dlg.display_plot_checkBox.isChecked():
            # Get the current canvas extent
            canvas_extent = iface.mapCanvas().extent()

            # Extract extent coordinates
            min_x, min_y = canvas_extent.xMinimum(), canvas_extent.yMinimum()
            max_x, max_y = canvas_extent.xMaximum(), canvas_extent.yMaximum()


            bbox_param = f"{min_y},{min_x},{max_y},{max_x}"

            url = 'https://data.geopf.fr/wfs/ows'
            params = {
                'service': 'WFS',
                'version': '1.1.0',  # WFS version
                'request': 'GetFeature',
                'TYPENAME': 'CADASTRALPARCELS.PARCELLAIRE_EXPRESS:parcelle',
                "bbox": bbox_param,
                'outputFormat': 'json',  # Get the response as GeoJSON
            }


            # Send the request to the WFS server
            response = requests.get(url, params=params)


            self.update_layer(self.all_plot_layer_name,response.json()) #update the all plot layer

            self.plotwindow = PlotWindow(self.all_plot_layer_name)
            self.set_side_position_for_dialogs(self.plotwindow.dlg,10)
            self.plotwindow.dlg.show()
            self.plotwindow.dlg.send.clicked.connect(self.add_plot)

            self.plotwindow.dlg.rejected.connect(self.hide_all_plot_window)


        else:
            self.hide_all_plot_window()

    def toggle_plu_display(self):
        """Toggle the Display of the PLU"""
        layer_name = "wfs_du:zone_urba"
        if self.dlg.display_plu_checkBox.isChecked():
            self.delete_already_existing_layer(layer_name)
            self.plu_layer = self.create_wfs_layer(layer_name)
            if self.plu_layer:
                stylefile_path = os.path.join(Path(__file__).parent, 'qgis_style_files', 'plu_style.qml')
                self.plu_layer.loadNamedStyle(stylefile_path)
        else:
            if self.plu_layer:
                QgsProject.instance().removeMapLayer(self.plu_layer)
                self.iface.mapCanvas().refresh()

    def toggle_rpg_display(self):
        """Toggle the Display of the RPG"""
        layer_name = "RPG.2023:parcelles_graphiques"
        if self.dlg.display_rpg_checkBox.isChecked():
            self.delete_already_existing_layer(layer_name)
            self.rpg_layer = self.create_wfs_layer(layer_name)
            if self.rpg_layer:
                stylefile_path = os.path.join(Path(__file__).parent, 'qgis_style_files', 'rpg_style.qml')
                self.rpg_layer.loadNamedStyle(stylefile_path)
        else:
            if self.rpg_layer:
                QgsProject.instance().removeMapLayer(self.rpg_layer)
                self.rpg_layer = None
                self.iface.mapCanvas().refresh()

    def toggle_protected_display(self):
        """Toggle the Display of the 4 type of protected areas"""
        for name in self.protected_layers.keys():
            if self.dlg.display_protected_checkBox.isChecked():
                self.delete_already_existing_layer(name)
                self.protected_layers[name] = self.create_wfs_layer(name)

            else:
                if self.protected_layers[name]:
                    QgsProject.instance().removeMapLayer(self.protected_layers[name])
                    self.protected_layers[name] = None
                    self.iface.mapCanvas().refresh()

    def create_wfs_layer(self, wfs_layer_name):
        """load a WFS layer from geoportail using it's reference name
        :param wfs_layer_name: name of the geoportail layer to import
        :type wfs_layer_name: str
        """
        wfs_url = f"WFS:// pageSize='10000' pagingEnabled='true' preferCoordinatesForWfsT11='false' restrictToRequestBBOX='1' srsname='EPSG:4326' typename='{wfs_layer_name}' url='https://data.geopf.fr/wfs/ows' version='1.1.0'"

        layer = QgsVectorLayer(wfs_url, wfs_layer_name, "WFS")
        if layer.isValid():
            QgsProject.instance().addMapLayer(layer)
            print("WFS layer loaded successfully!")
            return layer
        else:
            print("Failed to load WFS layer.")
            return None

    def hide_all_plot_window(self):
        """Correctly close the window to add plots. Allow to hide the layer showing all the plots at the same time"""
        if self.dlg.display_plot_checkBox.isChecked():
            self.dlg.display_plot_checkBox.setChecked(False)
        if self.plotwindow:
            self.plotwindow.dlg.rejected.disconnect()
            self.plotwindow.dlg.done(0)
        layer_list = QgsProject.instance().mapLayersByName(self.all_plot_layer_name)
        if layer_list:
            layer = layer_list[0]
            QgsProject.instance().removeMapLayer(layer)
            self.iface.mapCanvas().refresh()

    def add_plot(self):

        self.synchronizer.add_element_to_monday(self.plotwindow.plot_infos)
        self.sync()


    def writeLog(self,text):
        """Overwrite a message into the log widget
            :params text: the string to display
            :type text: str"""
        self.dlg.log.setText(text)

    def appendLog(self,text):
        """Append a message into the log widget
            :params text: the string to display
            :type text: str"""
        a_text = self.dlg.log.toPlainText() + '\n'
        self.dlg.log.setText(a_text+text)

    def delete_already_existing_layer(self,layer_name):
        """check by layer name if a layer already exists and delete it
        :param layer_name : string of the layer to delete name"""
        layer_list = QgsProject.instance().mapLayersByName(layer_name)
        if layer_list:
            layer = layer_list[0]
            QgsProject.instance().removeMapLayer(layer)

    def close(self):
        iface.edition_window = None

        if self.sync_worker:
            self.sync_worker.wait()



