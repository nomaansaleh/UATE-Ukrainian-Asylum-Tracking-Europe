import requests
import psycopg2
from psycopg2 import sql

# get coordinates for a country name using Google Geocoding API
def get_coordinates(country_name, api_key):
    geo_url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {"address": country_name, "key": api_key}
    response = requests.get(geo_url, params=params)
    if response.status_code == 200 and response.json()['results']:
        result = response.json()["results"][0]["geometry"]["location"]
        return result["lat"], result["lng"]
    else:
        return None, None

# Database credentials
db_params = {
    "db parameters"
}

# Connect to the database
conn = psycopg2.connect(**db_params)
cursor = conn.cursor()

# Check if the table exists, and delete it if it does
cursor.execute(f"DROP TABLE IF EXISTS asylum_applications")
# Update table schema to include POINT data type for COA coordinates
cursor.execute("""
    CREATE TABLE IF NOT EXISTS asylum_applications (
        id SERIAL,
        year INTEGER,
        coo_name TEXT,
        coa_name TEXT,    
        app_type TEXT,
        dec_level TEXT,
        applied INTEGER,
        shape GEOMETRY(POINT, 4326)
    );
""")
conn.commit()

# Google Geocoding API key
google_api_key = 'API KEY'

# UNHCR API endpoint and parameters
url = "https://api.unhcr.org/population/v1/asylum-applications/"
year_range = range(2013, 2023)
coo = "UKR"
coa_countries = ["AUT", "DEU", "ITA", "GBR", "SWE", "SWI", "FRA", "ESP", "NLD", "BEL", "GRC", "PRT", "POL"]

# Loop through the coa_countries and years
for coa in coa_countries:
    for year in year_range:
        # Define API request parameters
        params = {
            "limit": 100,
            "yearFrom": year,
            "yearTo": year,
            "coo": coo,
            "app_type": "N",
            "coa": coa,
            "cf_type": "iso"
        }

        # Make the API request
        response = requests.get(url, params=params)
        if response.status_code == 200:
            data = response.json()

            # Process and insert data
            for item in data.get("items", []):
                if item.get("app_type") == "N":  # Check if the app_type is 'N'
                    coa_name = item.get("coa_name", "")
                    coa_lat, coa_lng = get_coordinates(coa_name, google_api_key)

                    # Insert data into the database
                    if coa_lat is not None and coa_lng is not None:
                        cursor.execute(sql.SQL("""
                            INSERT INTO asylum_applications (
                                year, coo_name, coa_name, app_type, dec_level, applied, shape
                            ) VALUES (%s, %s, %s, %s, %s, %s, ST_PointFromText('POINT(%s %s)', 4326))
                        """), (year, item['coo_name'], coa_name, item['app_type'], item['dec_level'], item['applied'], coa_lng, coa_lat))
                    conn.commit()
        else:
            print(f"Failed to retrieve data for year={year}, coa={coa}. Status code: {response.status_code}")

# Close the connection
cursor.close()
conn.close()

print("Data has been written to the PostgreSQL database with COA coordinates for app_type 'N'.")
