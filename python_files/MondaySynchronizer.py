import requests
import json
import ast
import time
from pathlib import Path
import os
import datetime
from dateutil import parser
import webbrowser
from threading import Thread

class MondaySynchronizer:
    """Manage the connection from or to the Monday database with a local geojson database. Key user is Paul Poissonnet"""


    apiKey = "eyJhbGciOiJIUzI1NiJ9.eyJ0aWQiOjQzNjA4NjcwNiwiYWFpIjoxMSwidWlkIjo2NTg5MjkyOCwiaWFkIjoiMjAyNC0xMS0xM1QxMjo1NTozNS4wNjVaIiwicGVyIjoibWU6d3JpdGUiLCJhY3RpZCI6MTU2NTE0MzMsInJnbiI6ImV1YzEifQ.JOq8JPaRwXaRS5kP0EowpK8Fwv3L2RdcljxpaTkLX8c"
    apiUrl = "https://api.monday.com/v2"
    headers = {"Authorization": apiKey}
    board_id = 1719340424
    name_main_group = "nouveau_groupe14626__1"

    geom_column_infos ={
        "name":"Géométrie"
    }


    intersting_attributes = {
        "Qualité":{},
        "En charge":{},
        "Commune":{},
        "Etat": {},
        'Région':{},
        'Brique Techno':{},
        'Protocole':{},
        'Poste Source':{},
        "Code Postal":{},
        "Propriétaire": {},

    }
    relative_path = Path(__file__).parent
    save_json_file_name = "monday_items_json.json"

    def __init__(self):
        """Constructor."""
        self.all_items = []
        self.get_column_position_by_attribute()
        self.geojson_dict = {}
        self.parameters = {}
        parameters_thread = Thread(target=self.get_monday_parameters)  # Parralel launch to earn some time
        parameters_thread.start()


        if os.path.isfile(os.path.join(self.relative_path,self.save_json_file_name)):
            self.load_from_file()



    def load_all_data_from_monday(self):
        """Reads all the data from the Monday database and store it in a local file"""

        self.geojson_dict = {
            "type": "FeatureCollection",
            "features": []
        } #init the geojson format
        print("--")
        print("--")

        print("creating new dic from scratch")
        old_date = datetime.datetime.fromtimestamp(1, tz=datetime.timezone.utc) #simulate a very old date to be sure everything is synched
        ids, names = self.get_plot_id_list(old_date, 500)
        self.get_plots_by_id_list(ids)

        self.update_geojson_dict()

        self.save_to_file()
        self.get_monday_parameters() #For further use in an edition window

    def sync(self):
        """Reads the data from monday and update the local database if new updates are detected"""

        if not os.path.isfile(os.path.join(self.relative_path, self.save_json_file_name)):
            self.load_all_data_from_monday() #If all data have to be retrieved
            return ''
        last_sync_date = datetime.datetime.fromtimestamp(os.path.getmtime(os.path.join(self.relative_path,self.save_json_file_name)),tz=datetime.timezone.utc)

        ids, allnames = self.get_plot_id_list(last_sync_date)
        self.delete_from_dic_by_name(allnames)

        parameters_thread = Thread(target=self.get_monday_parameters) #Parralel launch to earn some time
        parameters_thread.start()
        get_plots_thread = Thread(target=self.get_plots_by_id_list, args=(ids,))
        get_plots_thread.start()

        get_plots_thread.join()
        parameters_thread.join()

        self.update_geojson_dict()
        print("items imported : "+str(len(self.geojson_dict["features"])))
        self.save_to_file()

    def get_plot_id_list(self,last_sync_date,items_per_page=500):
        """Gets the ids of all the plots which have been modified or created since last_sync_date
        Also returns the list of names of all the plots present in the database
            :param last_sync_date: the date from which the method will store updated items
            :type last_sync_date: datetime
            :param items_per_page: max size of the queries
            :type items_per_page: int
            :return: int list containing the ids of elements to update and
            str list containing the names of all elements in the board"""

        plot_id_list = []
        all_plot_names = []
        query = f"""{{boards (ids:{self.board_id}) {{
            items_page (limit:{items_per_page},query_params: {{order_by : {{column_id : "__last_updated__", direction : desc}}}}) {{
                cursor
                items{{
                    id
                    name
                    state
                    updated_at
                }}
    }} }} }}"""
        response = requests.post(self.apiUrl, json={'query': query}, headers=self.headers)
        data = response.json()


        for plot in data['data']['boards'][0]["items_page"]['items']:
            all_plot_names.append(plot["name"])
            last_updated = parser.parse(plot["updated_at"])
            if last_updated>last_sync_date and plot["state"]=='active':
                plot_id_list.append(int(plot["id"]))


        cursor = data['data']['boards'][0]["items_page"]['cursor']

        while cursor: #reads the next item page while there is one to read
            query = f"""{{
                   next_items_page(limit: {items_per_page}, cursor: "{cursor}") {{
                       cursor
                       items{{
                            id
                            name
                            state
                            updated_at
                            }}
                       }} }}"""

            response = requests.post(self.apiUrl, json={'query': query}, headers=self.headers)
            data = response.json()

            for plot in data['data']['next_items_page']['items']:
                all_plot_names.append(plot["name"])
                last_updated = parser.parse(plot["updated_at"])
                if last_updated > last_sync_date and plot['state']=='active':
                    plot_id_list.append(int(plot["id"]))

            cursor = data['data']['next_items_page']['cursor']
        print(f"{len(plot_id_list)} elems to update")
        return plot_id_list,all_plot_names


    def delete_from_dic_by_name(self, all_plot_names):
        """check if the local database contains elems that do not exist anymore in the Monday Database and delete them
        :param all_plot_names: str list containing the names of all the elements in the monday board"""
        unique_names =[]
        for elem in self.geojson_dict["features"][::-1]:
            if not elem["properties"]["idu"] in unique_names:
                unique_names.append(elem["properties"]["idu"])
                if not elem["properties"]["idu"] in all_plot_names:
                    self.geojson_dict["features"].remove(elem)
                    print(f'{elem["properties"]["idu"]} removed succesfully')
            else:
                self.geojson_dict["features"].remove(elem)
                print(f'{elem["properties"]["idu"]} was doubled, the copy was deleted')

    def get_plots_by_id_list(self, plot_id_list):
        """get the data from the monday boards plots from the id list given
        :param plot_id_list: int list containing the ids of the elem we want to retrieve the data from"""

        self.all_items = []
        id_sublist_size = 100
        for i in range(0, len(plot_id_list), id_sublist_size):
            sublist = plot_id_list[i:i + id_sublist_size]
            self.get_data_from_query(sublist)
            print(f"{i} elems retrieved from Monday on {len(plot_id_list)}")


    def update_geojson_dict(self):
        """Converts the Monday data previously retrieved into geojson dic format"""

        dropped_amount = 0

        for item in self.all_items:

            feature_dic = { # Initialize the shape of the feature dic
                "type":"Feature",
                "properties":{},
                "geometry":{}
            }



            for attribute in self.intersting_attributes.keys(): # find the value of each attribute

                column_id = self.intersting_attributes[attribute]["position"]
                if "linked_items" in item['column_values'][column_id].keys(): #if the element is a connect_board, then its value is stored in linked_items
                    if len(item['column_values'][column_id]['linked_items'])>0:
                        feature_dic['properties'][attribute] = item['column_values'][column_id]['linked_items'][0]["name"]
                    else :
                        feature_dic['properties'][attribute] = "not given"
                elif "display_value" in item['column_values'][column_id].keys():#if the element is a mirror, then its value is stored in display_value
                    feature_dic['properties'][attribute] = item['column_values'][column_id]['display_value']

                else:
                    feature_dic['properties'][attribute] = item['column_values'][column_id]['text']

            feature_dic['properties']['idu'] = item['name']
            feature_dic['properties']['monday_id'] = item['id']
            geom_index = self.geom_column_infos["position"]
            geom_dic_string = item['column_values'][geom_index]['text']

            try:
                feature_dic['geometry'] = ast.literal_eval(geom_dic_string)
                self.geojson_dict["features"].append(feature_dic)
            except Exception as inst:
                dropped_amount+=1
                if("invalid syntax" in inst.args):
                    print(item['name'] + " geom exceed 2000 characters or geom not indicated")
                else:
                    print(item['name'] + " unknown, was not loaded")
        print(f"{dropped_amount} elems have been dropped in the process")


    def get_column_position_by_attribute(self):
        """get the position in Monday of the columns containing the interesting attributes"""
        query = f"""{{boards(ids: {self.board_id}) {{
        columns{{
          id
          title}}}}}}"""
        response = requests.post(self.apiUrl, json={'query': query}, headers=self.headers)
        column_infos = response.json()

        i=0
        for column in column_infos['data']['boards'][0]['columns']:
            if column["title"] in self.intersting_attributes.keys():
                self.intersting_attributes[column["title"]]["id"] = column["id"]
                self.intersting_attributes[column["title"]]["position"]=i-1 #do not count the name column

            elif column["title"] == self.geom_column_infos["name"]:
                self.geom_column_infos["id"] = column["id"]
                self.geom_column_infos["position"] = i - 1  # do not count the name column


            i+=1



    def get_monday_parameters(self):
        """get the additional labels of the multichoice columns of monday """
        query = f"""{{boards(ids: {self.board_id}) {{
                           columns{{settings_str}}}}}}"""
        response = requests.post(self.apiUrl, json={'query': query}, headers=self.headers)

        tech_setting_str = \
        response.json()["data"]["boards"][0]["columns"][self.intersting_attributes["Brique Techno"]["position"] + 1][
            "settings_str"]
        tech_setting_dic = json.loads(tech_setting_str)
        labels = []
        for l in tech_setting_dic["labels"]:
            labels.append(l["name"])
        self.parameters["techno_list"] = labels

        status_setting_str = \
        response.json()["data"]["boards"][0]["columns"][self.intersting_attributes["Etat"]["position"] + 1][
            "settings_str"]

        status_setting_dic = json.loads(status_setting_str)
        self.parameters["status_list"] = list(status_setting_dic["labels"].values())


    def add_element_to_monday(self, plot_infos):
        """Add an element to the monday board
        :param plot_infos: dic containing the pairs of attributes/values to fill the monday board"""

        column_values = {}
        for attribute in self.intersting_attributes.keys():
            if attribute in plot_infos.keys():
                column_values[self.intersting_attributes[attribute]["id"]] = plot_infos[attribute]

        column_values[self.geom_column_infos["id"]] = str(plot_infos["Géometrie"]).replace('"', "'")
        #print(column_values)
        json_colum_values = json.dumps(column_values).replace('"','\\"').replace('\\'+'\\"','\\"')#.replace('{','\\{').replace('}','\\}').replace('[','\\[').replace(']','\\]')
        #json_colum_values = str(column_values)
        query = f"""mutation {{
  create_item (board_id: {self.board_id}, group_id: "{self.name_main_group}", item_name: "{plot_infos["idu"]}", column_values: "{json_colum_values}") {{
        id
      }}
    }}"""


        r = requests.post(url=self.apiUrl, json={'query': query}, headers=self.headers)  # make request
        print(r.content)

    def delete_element_in_monday(self, idu):
        """delete an element to the monday board from its idu
                :param idu: str containing the plot idu"""

        for elem in self.geojson_dict["features"]:
            if elem["properties"]["idu"] == idu:
                elem_id = elem["properties"]["monday_id"]
                self.geojson_dict["features"].remove(elem)
        Thread(target=self.delete_element_query,args = (elem_id,)).start() #Do not freeze the execution of the programm

    def delete_element_query(self, elem_id):
        """make the delete query to monday
        :param elem_id: str containing the plot idu"""

        query = f"""mutation {{delete_item (item_id: {elem_id}) {{id}}}}"""

        r = requests.post(url=self.apiUrl, json={'query': query}, headers=self.headers)  # make request
        print(r.content)

    def modify_element_to_monday(self, plot_infos):
        """Modify an element in the monday board
        :param plot_infos: dic containing the pairs of attributes/values to fill the monday board"""

        i = 0
        for elem in self.geojson_dict["features"]:
            if elem["properties"]["idu"]==plot_infos["idu"]:
                elem_id = elem["properties"]["monday_id"]
                elem_position = i
            i+=1
        column_values = {}
        for attribute in self.intersting_attributes.keys():
            if attribute in plot_infos.keys():
                column_values[self.intersting_attributes[attribute]["id"]] = plot_infos[attribute]
                if type({})==type(plot_infos[attribute]): #The rating elements are displayed as dic
                    self.geojson_dict["features"][elem_position]["properties"][attribute] = plot_infos[attribute]["rating"]
                else:
                    self.geojson_dict["features"][elem_position]["properties"][attribute] = plot_infos[attribute]


        # print(column_values)
        json_colum_values = json.dumps(column_values).replace('"', '\\"').replace('\\' + '\\"',
                                                                                  '\\"')  # .replace('{','\\{').replace('}','\\}').replace('[','\\[').replace(']','\\]')
        Thread(target=self.send_modification_query, args=(elem_id,json_colum_values)).start() #Launch in a thread to prevent freezing the process


    def send_modification_query(self, elem_id,json_colum_values):
        """Makes the modification query to monday
        :param json_colum_values: dic containing the pairs of attributes/values to fill the monday board"""
        query = f"""mutation {{
      change_multiple_column_values (board_id: {self.board_id}, item_id: {elem_id}, column_values: "{json_colum_values}") {{
        id
      }}
    }}"""

        r = requests.post(url=self.apiUrl, json={'query': query}, headers=self.headers)  # make request
        print(r.content)

    def save_to_file(self):
        """save the local database in a file under geojson format"""
        if len(self.geojson_dict)>0:
            with open(os.path.join(self.relative_path,self.save_json_file_name),'w') as file:
                json.dump(self.geojson_dict,file,indent=4)

    def load_from_file(self):
        """loads the local geojson database"""
        with open(os.path.join(self.relative_path,self.save_json_file_name),'r') as file:
            self.geojson_dict = json.load(file)

    def get_data_from_query(self,plot_id_sublist):
        """makes the query to retrieve data"""
        query = f"""{{
    items(limit:{len(plot_id_sublist)} ids: {plot_id_sublist}) {{
        id
        name
        group{{
            title
        }}
        column_values{{
            id
            value
            text
            ... on BoardRelationValue {{
                linked_item_ids
                linked_items{{
                    name
                }}
            }}
            ... on MirrorValue {{
                display_value
                id
            }}
        }}
    }}
    
    
    }}"""
        response = requests.post(self.apiUrl, json={'query': query}, headers=self.headers)
        try:
            data = response.json()
            items = data['data']['items']
            self.all_items.extend(items)
        except:
            if ("high-volume traffic" in response.text):
                print("requesting the API too much, need to sleep 30s")
                time.sleep(30)
                self.get_data_from_query(plot_id_sublist)











    def open_in_browser(self,idu):
        url = f"""https://wattmen.monday.com/boards/1719340424?term={idu}&termColumns=XQAAAAIeAAAAAAAAAABBKoIjYcac_KBY4EB0iAHQOZ9yB41kRY_qRcch_98tAAA"""
        webbrowser.open(url)

    def open_in_google_maps(self,geom):
        geom = json.loads(geom)

        y=geom["coordinates"][0][0][0][0]
        x = geom["coordinates"][0][0][0][1]
        url ="https://www.google.com/maps/dir//" + str(x) + "," + str(y)
        webbrowser.open(url)






