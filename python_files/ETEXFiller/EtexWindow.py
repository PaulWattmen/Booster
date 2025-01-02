from .python_files.Plot import Plot
from .python_files.RteFormFiller import RteFormFiller
from .python_files.AerialViewer import AerialViewer
from .python_files.GeofoncierScreener import GeofoncierScreener
import time
import os
from PyQt5.QtCore import Qt
from .Etex_Window.etex_dialog import EtexDialog
from pathlib import Path

class EtexWindow():
    def __init__(self,plot_infos):
        self.plot_infos = plot_infos

        self.dlg = EtexDialog()
        self.dlg.plot_lineEdit.setText(self.plot_infos["idu"])
        self.dlg.output_folder_lineEdit.setText(os.path.dirname(os.path.abspath(__file__)))

        if os.name == "nt":  # if running on windows
            self.dlg.setWindowFlags(Qt.WindowStaysOnTopHint)
        self.dlg.autocad_button.clicked.connect(self.create_autocad_files)
        self.dlg.form_button.clicked.connect(self.fill_RTE_form)


    def create_autocad_files(self):

        main_dir_path = self.dlg.output_folder_lineEdit.text()
        params_folder = os.path.join(main_dir_path, 'parameters_files/')
        pic_folder = os.path.join(main_dir_path, 'pictures/')

        if not os.path.exists(main_dir_path):
            self.writeLog("Erreur : dossier de sortie inexistant")
            return ''
        elif not os.path.exists(params_folder):
            Path(params_folder).mkdir(parents=True, exist_ok=True)
        if not os.path.exists(pic_folder):
            Path(pic_folder).mkdir(parents=True, exist_ok=True)

        plot = self.get_all_attributes()

        plot.save_attributes_to_file(os.path.join(main_dir_path, 'parameters_files/autocad_fill_cartridge.txt'))

        viewer = AerialViewer()

        bounds = 0.00005
        viewer.get_img(plot.attributes["wkt"],bounds)
        viewer.calculate_coordinates_in_meters()
        viewer.save_pic(os.path.join(main_dir_path, 'pictures/autocad_aerial_view_small.png'))
        viewer.save_metadata(os.path.join(main_dir_path, 'parameters_files/autocad_coordinates_params_small.txt'))

        bounds = 0.005
        viewer.get_img(plot.attributes["wkt"],bounds)
        viewer.calculate_coordinates_in_meters()
        viewer.save_pic(os.path.join(main_dir_path, 'pictures/autocad_aerial_view_big.png'))
        viewer.save_metadata(os.path.join(main_dir_path, 'parameters_files/autocad_coordinates_params_big.txt'))

        viewer.save_meters_geometry_to_file(os.path.join(main_dir_path, 'parameters_files/polygon_geometry.txt'))

        GeofoncierScreener().get_pic(os.path.join(main_dir_path, 'pictures/cadastre.png'),plot.attributes["idu"])


        self.appendLog("Fichiers et images pour autocad créées avec succès !")

    def fill_RTE_form(self):

        main_dir_path = self.dlg.output_folder_lineEdit.text()
        param_file_path = os.path.join(main_dir_path, 'parameters_files/params.json')
        print(param_file_path)
        if not os.path.exists(param_file_path):
            self.writeLog("Erreur : dossier de sortie inexistant")
            return ''

        plot = self.get_all_attributes()

        formfiller = RteFormFiller(param_file_path)
        if formfiller.open_form() ==-1:
            self.writeLog("Connectez-vous, fermez la fenêtre puis recliquez sur le bouton")
            return ''
        time.sleep(0.5)
        formfiller.fill_form(plot.attributes)

        self.appendLog("Formulaire complété avec succès !")

    def get_all_attributes(self):
        plot = Plot(self.plot_infos['idu'])
        plot.get_plot_data_from_monday()
        plot.get_attributes_from_pappers()
        self.writeLog(plot.attributes["geofoncier_link"])
        return plot




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