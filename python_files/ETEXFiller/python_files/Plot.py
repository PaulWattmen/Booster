import requests
import ast
from datetime import datetime
import json

PAPPERS_HEADERS = {
    "Host": "api-immobilier.pappers.fr",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:130.0) Gecko/20100101 Firefox/130.0",

    "Content-Type": "application/json",
    "Authorization": "Bearer 423daecc878d51b79f0df6bce6c20341eb5db2fcb39f1d2a",
    "Origin": "https://immobilier.pappers.fr",
    "Connection": "keep-alive",
    "Referer": "https://immobilier.pappers.fr/",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-site",
    "Priority": "u=0",
    "TE": "trailers"
    }
PAPPERS_URL = 'https://api-immobilier.pappers.fr/v1/recherche-parcelles'

class Plot:

    apiKey = "eyJhbGciOiJIUzI1NiJ9.eyJ0aWQiOjQzNjA4NjcwNiwiYWFpIjoxMSwidWlkIjo2NTg5MjkyOCwiaWFkIjoiMjAyNC0xMS0xM1QxMjo1NTozNS4wNjVaIiwicGVyIjoibWU6d3JpdGUiLCJhY3RpZCI6MTU2NTE0MzMsInJnbiI6ImV1YzEifQ.JOq8JPaRwXaRS5kP0EowpK8Fwv3L2RdcljxpaTkLX8c"
    apiUrl = "https://api.monday.com/v2"
    headers = {"Authorization": apiKey}
    board_id = 1719340424

    def __init__(self,idu):
        self.comm_column_id = "commune__1"
        self.insee_column_id = "code_postal7__1"
        self.station_column_id = 'connecter_les_tableaux9__1'
        self.geom_column_id = 'long_texte__1'
        self.attributes = {}
        self.attributes["idu"] = idu


    def get_plot_data_from_monday(self):



        query = f"""{{ boards (ids:{self.board_id}) {{
                      items_page (limit :1,query_params:{{rules:[{{column_id: "name", compare_value: "{self.attributes["idu"]}", operator: any_of}}]}}) {{
                        items {{
                        id
                        column_values{{
                        id
                        text
                        ... on BoardRelationValue {{
                        linked_items {{
                        name

                    }}
                        }}
                        }}
                        }} }} }} }}"""

        r = requests.post(url=self.apiUrl, json={'query': query}, headers=self.headers)  # make request
        print(r.content)
        data = r.json()

        self.extract_interesting_attributes_from_data(data)

    def extract_interesting_attributes_from_data(self,data):

        for cell in data["data"]["boards"][0]["items_page"]["items"][0]["column_values"]:
            if cell["id"] == self.comm_column_id:
                self.attributes["commune"] = cell["text"]
            elif cell["id"] == self.insee_column_id:
                self.attributes["INSEE"] = cell["text"]
            elif cell["id"] == self.geom_column_id:
                self.attributes["wkt"] = ast.literal_eval(cell["text"])
                self.attributes["longitude"] = round(self.attributes["wkt"]["coordinates"][0][0][0][0],5)  # format [longitude, latitude]
                self.attributes["latitude"] = round(self.attributes["wkt"]["coordinates"][0][0][0][1], 5)
            elif cell["id"] == self.station_column_id:
                self.attributes["ps_name"] = cell['linked_items'][0]['name']
                self.attributes["nom projet"] = "PROJET " + self.attributes["ps_name"]

    def get_attributes_from_pappers(self):
        payload = {"parcelle_cadastrale": self.attributes["idu"],
                   "colonnes": "coordonnees",
                   "champs_supplementaires": "tous",
                   "bases": "tous"}
        response = requests.post(PAPPERS_URL, data=json.dumps(payload), headers=PAPPERS_HEADERS)

        data_list_ans = response.json()
        if len(data_list_ans["resultats"]) != 0: #Si la parcelle existe dans la DB PAPPERS
            self.attributes["adresse_comm"] = data_list_ans["resultats"][0]["codes_postaux"][0] + " " + data_list_ans["resultats"][0][
                "commune"]
            self.attributes["adresse_voie"] = data_list_ans["resultats"][0]["adresse"]
        else:
            print("not found")

        self.attributes["geofoncier_link"] = "https://public.geofoncier.fr/?utm_source=geofoncier.fr&utm_medium=Referral&utm_campaign=btn-menu-public&parcelle=" + self.attributes["idu"]

    def save_attributes_to_file(self, file_name):
        # params.txt avec toutes les infos textuelles pour autocad

        str = ""
        today = datetime.today()
        formatted_date = today.strftime("%d/%m/%Y")

        str+=self.attributes["nom projet"] + "\n"
        str+= self.attributes["adresse_comm"] + "\n"
        str += self.attributes["adresse_voie"] + "\n"
        str += "POSTE RTE " + self.attributes["ps_name"] + "\n"
        str += self.attributes["idu"] + "\n"
        str += formatted_date + "\n"
        str += formatted_date

        with open(file_name, "w") as file:
            file.write(str)



