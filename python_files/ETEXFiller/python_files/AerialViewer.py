from pyproj import Transformer
from shapely.geometry import shape, MultiPolygon
import requests

class AerialViewer:
    def __init__(self):
        self.export_url = "https://services.arcgisonline.com/arcgis/rest/services/World_Imagery/MapServer/export"
        self.pic = {}

    def save_meters_geometry_to_file(self,file_name):

        transformer = Transformer.from_crs("EPSG:4326", "EPSG:3857")

        mcoords = []

        for coords in self.pic["wkt"]["coordinates"][0][0]:
            x, y = transformer.transform(coords[0], coords[1])
            mcoords.append([-(x - self.pic["x_offset_meters"]), y - self.pic["y_offset_meters"]])

        str = ""
        for c in mcoords:
            str += f'{c[0] : .2f},{c[1] : .2f}\n'

        with open(file_name, "w") as file:
            file.write(str)

    def get_geometry_box(self,wkt):
        # Convert the GeoJSON geometry to a Shapely MultiPolygon object

        multipolygon = shape(wkt)

        # Ensure we are working with a MultiPolygon type
        if not isinstance(multipolygon, MultiPolygon):
            multipolygon = MultiPolygon([multipolygon])

        min_x, min_y, max_x, max_y = multipolygon.bounds

        return min_x, min_y, max_x, max_y

    def get_img(self,wkt, bounds):

        self.pic["wkt"]=wkt

        min_x, min_y, max_x, max_y = self.get_geometry_box(wkt)

        params = {

            "bbox": f"{min_x - bounds},{min_y - bounds},{max_x + bounds},{max_y + bounds}",
            # min_lon, min_lat, max_lon, max_lat
            "bboxSR": "4326",  # Spatial reference system for bbox
            "imageSR": "4326",  # Spatial reference system for output image
            "size": "1080,720",  # Image size (width, height)
            "format": "png",  # Output format
            "f": "pjson"  # Response format (image or metadata)
        }

        # Make the request to get the real boundaries of the pic
        response = requests.get(self.export_url, params=params)
        #print(response.json())
        r = response.json()["extent"]


        self.pic["scale"] = response.json()["scale"]
        self.pic["x_min_degrees"] = r["xmin"]
        self.pic["y_min_degrees"] = r["ymin"]

        # Centre l'image sur le premier point du polygone
        self.pic["x_offset_degrees"] = wkt["coordinates"][0][0][0][0]
        self.pic["y_offset_degrees"] = wkt["coordinates"][0][0][0][1]


        params["f"] = "image"

        # Make the request to get the effective picture
        response = requests.get(self.export_url, params=params)

        # Save the image to a file
        if response.status_code == 200:

            self.pic["png"] = response.content
            print(f"Picture retrived with bounds : {round(bounds,5)}")

        else:
            if bounds < 0.008:
                #Maybe the image trying to be retrieved is too small. Trying with larger bounds
                print(f"Failed to retrieve picture. Trying with larger boundaries. Actual bounds : {round(bounds,5)}")
                bounds += 0.00005
                self.get_img(wkt,bounds)
            else:
                print("ERROR : Failed to retrieve image.")

    def calculate_coordinates_in_meters(self):

        transformer = Transformer.from_crs("EPSG:4326", "EPSG:3857")

        self.pic["x_offset_meters"],self.pic["y_offset_meters"] = transformer.transform(self.pic["x_offset_degrees"], self.pic["y_offset_degrees"])
        self.pic["min_x_meters"], self.pic["min_y_meters"] = transformer.transform(self.pic["x_min_degrees"], self.pic["y_min_degrees"])

    def save_pic(self,file_name):
        with open(file_name, "wb") as file:
            file.write(self.pic["png"])


    def save_metadata(self,file_name):
        if self.pic["min_x_meters"]:
            str = ""
            str += f'{-self.pic["min_x_meters"] + self.pic["x_offset_meters"] :.2f},{self.pic["min_y_meters"] - self.pic["y_offset_meters"] : .2f}\n'
            str += f'{self.pic["scale"] :.2f}\n'

            with open(file_name, "w") as file:
                file.write(str)
        else:
            print("Coordinates need to be calculated in meters before being exported")


