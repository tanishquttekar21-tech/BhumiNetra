def generate_gis_parcel_data(survey_no, state="Maharashtra", village="Wagholi"):
    """
    GIS Engine:
    Generates spatial polygon boundary coordinates, centroid lat/long,
    area calculation, and GeoJSON parcel attributes for Leaflet map mapping.
    """
    # Default base coordinates for sample locations
    location_base = {
        "Wagholi": {"lat": 18.5793, "lng": 73.9806, "district": "Pune"},
        "Vijayapura": {"lat": 13.2925, "lng": 77.7275, "district": "Bengaluru Rural"},
        "Phulpur": {"lat": 25.5492, "lng": 82.8804, "district": "Varanasi"},
        "Custom Plot": {"lat": 18.5204, "lng": 73.8567, "district": "Pune"}
    }
    
    base = location_base.get(village, {"lat": 18.5204, "lng": 73.8567, "district": "Pune"})
    c_lat, c_lng = base["lat"], base["lng"]
    
    # Generate 5-point polygon around centroid simulating cadastral survey plot boundary
    offset = 0.0018
    polygon_coords = [
        [c_lat + offset * 0.8, c_lng - offset * 1.0],
        [c_lat + offset * 1.2, c_lng + offset * 0.6],
        [c_lat - offset * 0.4, c_lng + offset * 1.1],
        [c_lat - offset * 1.0, c_lng - offset * 0.2],
        [c_lat - offset * 0.6, c_lng - offset * 0.9],
        [c_lat + offset * 0.8, c_lng - offset * 1.0] # Close ring
    ]
    
    geojson_feature = {
        "type": "Feature",
        "geometry": {
            "type": "Polygon",
            "coordinates": [[[lng, lat] for lat, lng in polygon_coords]] # GeoJSON is [lng, lat]
        },
        "properties": {
            "survey_no": survey_no,
            "village": village,
            "district": base["district"],
            "state": state,
            "centroid": [c_lat, c_lng]
        }
    }
    
    return {
        "centroid": {"lat": c_lat, "lng": c_lng},
        "polygon_latlngs": polygon_coords,
        "geojson": geojson_feature
    }
