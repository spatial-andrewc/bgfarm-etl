import json
import geojson
from geojson import FeatureCollection, Feature
from shapely.geometry import LineString
from pyproj import Proj, transform


class Waypoints(dict):
    """
    A class representing a Deck.gl Trips array
    """

    def __init__(self, coordinates=None):
        """
        :param coordinates: a list of [x, y, time] lists derived from
        a geojson LineString's coordinates array
        :type iterable: list
        :return: an array of Waypoints
        """
        super().__init__(self)
        self.coordinates = coordinates
        if coordinates:
            self["waypoints"] = self.__set_coords()

    def __set_coords(self):
        return [{"coordinates": [pair[0], pair[1]], "timestamp": pair[2]} for pair in self.coordinates]


class Trip:
    """
    A class that converts a unique formatted LineString FeatureCollection
    into Kepler.gl geojson or Deck.gl array for Trips animation
    """

    def __init__(self, json_input, geographic_crs, projected_crs):
        """
        Initialises a json input and sets Trip geographic and projected crs
        :param json_input: formatted LineString FeatureCollection
        :type json_input: json/geojson string
        :param geographic_crs: geographic crs - will likely hard code to wgs84 in future
        :type geographic_crs: str
        :param projected_crs: local projected crs (calculates lengths in meters)
        :type projected_crs: str
        """
        self.json_input = self.__to_json(json_input)
        self.start_time = 1583884800
        self.m_per_second = 10
        self.geographic_crs = geographic_crs
        self.projected_crs = projected_crs

    
    def __to_json(self, json_input):
        with open(json_input) as this_json:
            return json.load(this_json)


    def __get_distance(self, coords_1, coords_2):
        """
        calculates length in meters between two coordinate pairs

        :param coords_1: lon,lat pair of point 1
        :param coords_2: lon, lat pair of point 2
        :type coords_1 coords_2: list, tuple
        """
        x1 = coords_2[0]
        y1 = coords_2[1]
        x2 = coords_1[0]
        y2 = coords_1[1]
        projected_y1, projected_x1 = transform(self.geographic_crs, self.projected_crs, y1, x1)
        projected_y2, projected_x2 = transform(self.geographic_crs, self.projected_crs, y2, x2)
        length = LineString([(projected_x1, projected_y1), (projected_x2, projected_y2)]).length
        return length

    def __json_iterator(self, output_type):
        """
        Iterates over all linestring coordinates and adds a 'visit time' to
        each pair. The 'visit time' explains the timestamp that the point is 
        visited
        """

        feature_list = []

        for x, item in enumerate(self.json_input['features']):
            if x == 0:
                time = self.start_time
            else:
                distance_from_start = item['properties']['distance']
                time = int(self.start_time + distance_from_start / self.m_per_second)
            
            this_coords = [_ for sublist in item['geometry']['coordinates'] for _ in sublist]

            for i, pair in enumerate(this_coords):
                j = i - 1
                if i == 0:
                    pair.append(time)
                else:
                    line_length = self.__get_distance(this_coords[j], pair)
                    time += int(line_length / self.m_per_second)
                    pair.append(time)
            
            if output_type == "json":
                this_linestring = geojson.LineString(this_coords)
                this_feature = Feature(geometry=this_linestring, type="Feature")
                feature_list.append(this_feature)
            
            elif output_type == "waypoints":
                feature_list.append(Waypoints(this_coords))
        return feature_list


    def generate_trips(self, output_type, start_time = None, m_per_second = None):
        """
        Generates a Trips object in the format requested as per the output_type

        :param output_type: type of output that is required - accepts 'json' or 'waypoints'
        :type output_type: str
        """

        if start_time:
            self.start_time = start_time
        if m_per_second:
            self.m_per_second = m_per_second

        if output_type == 'json'.lower():
            features = self.__json_iterator("json")
            output = FeatureCollection(features)
        
        elif output_type == 'waypoints'.lower():
            output = self.__json_iterator("waypoints")

        return output