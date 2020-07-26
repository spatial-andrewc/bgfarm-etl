import json
from shapely.geometry import LineString, Point
from shapely.ops import transform
import geojson
from pyproj import Transformer, Proj


class TripsGenerator:

    """
    A class that takes a geojson feature collection and returns an array of 
    Deck.gl Waypoints for the Trips geo-layer
    """

    def __init__(self, geojson_input):
        """
        Parameters
        ----------
        geojson_input: geojson feature or feature collection
        """
        self.geojson_input = self._to_json(geojson_input)


    def generate(self):
        """
        Convert all incoming geojson features into Shapely LineStrings
        to feed into the Trip class that returns a Deck GL Trips Waypoint
        object 
        """
        features = self.geojson_input['features']
        coords_list = map(lambda x: geojson.utils.coords(x), features)
        linestrings = [LineString(coords) for coords in coords_list]

        output_data = [Trip(linestring).run() for linestring in linestrings]
        
        maximum_timestamp = max([stop['timestamp'] for linestring in output_data for stop in linestring['waypoints']])
        
        return { 'DATA': output_data, 'MAXIMUM': maximum_timestamp }



    def _to_json(self, geojson_input):
        with open(geojson_input) as this_json:
            return json.load(this_json)

        

class Waypoints(dict):
    """
    A class representing a Deck.gl Trips array
    """

    def __init__(self, stops):
        """
        Parameters
        ----------
        stops: a list of [(x, y), time] lists derived from
        a geojson LineString's coordinates array

        Returns an array of Waypoints for Deck GL Trips consumption
        """
        super().__init__(self)
        self.stops = stops
        if self.stops:
            self["waypoints"] = self._set_coords()

    
    def _set_coords(self):
        return [{"coordinates": stop[0], "timestamp": stop[1]} for stop in self.stops]


class Trip:

    """
    Converts a LineString's array into projected coordinates and
    calculates the time taken to travel between each LineString's
    node
    """

    TIME = 0

    def __init__(self, linestring):
        """
        Parameters
        ----------
        linestring: A Shapely Linestring object 
        """
        self.linestring = linestring


    def run(self):
        """
        Performs the calculations for each linestring and 
        returns a Waypoint Object
        """
        _to_crs = 'epsg:28355'

        projected_linestring = self._reproject_linestring(_to_crs, self.linestring)
        projected_coords = list(projected_linestring.coords)

        geo_coords = list(self.linestring.coords)
        stop_times = self._get_stop_times(projected_coords)

        stops_zipped = zip(geo_coords, stop_times)
        return Waypoints(stops_zipped)

    
    def _reproject_linestring(self, to_crs, linestring):
        """ Reprojects from wgs84 to planar crs """
        project = Transformer.from_proj(Proj('epsg:4326'), Proj(to_crs), always_xy=True)
        return transform(project.transform, linestring)

    
    def _get_stop_times(self, projected_coords):
        """ Calculates the time between each point based on a m_per_second attribute"""
        time = Trip.TIME
        m_per_second = 40
        time_list = []

        for idx, stop in enumerate(projected_coords):
            j = idx - 1
            if idx == 0:
                time_list.append(Trip.TIME)
            else:
                path_length = Point(projected_coords[j]).distance(Point(stop))
                Trip.TIME += int(path_length / m_per_second)
                time_list.append(Trip.TIME)
        stop_times = tuple(time_list)
        return stop_times


    
