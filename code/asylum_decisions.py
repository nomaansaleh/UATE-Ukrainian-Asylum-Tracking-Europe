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
    "db params"
}

# Connect to the PostgreSQL database
conn = psycopg2.connect(**db_params)
cursor = conn.cursor()

# Google Geocoding API key
google_api_key = 'API KEY'  

# Define the priority order for decision levels
decision_level_priority = {
    "FI": 1,  # Final
    "NA": 2,  # National
    "FA": 3,  # First Appeal
    "RA": 4,  # Rejected Appeal
    "JR": 5,  # Judicial Review
    "AR": 6,  # Administrative Review
   
}

table_name = "asylum_decisions"
# Check if the table exists, and delete it if it does
cursor.execute(f"DROP TABLE IF EXISTS {table_name}")

# Create the table with the schema including coordinates
cursor.execute(f"""
    CREATE TABLE IF NOT EXISTS {table_name} (
        year INTEGER,
        coo_name TEXT,
        coa_name TEXT,
        procedure_type TEXT,
        dec_level TEXT,
        dec_recognized INTEGER,
        dec_other INTEGER,
        dec_rejected INTEGER,
        dec_closed INTEGER,
        dec_total INTEGER,
        coa_point GEOMETRY(POINT, 4326)
    );
""")
conn.commit()

# Base API endpoint URL
url = "https://api.unhcr.org/population/v1/asylum-decisions/"

# Define the parameters
year_range = range(2013, 2023)
coo = "UKR"
coa_countries = ["AUT", "DEU", "ITA", "GBR", "SWE", "SWI", "FRA", "ESP", "NLD", "BEL", "GRC", "PRT", "POL"]

# Dictionary to store the highest priority record for each year
highest_priority_records = {}

# Loop through the coa_countries and years
for coa in coa_countries:
    for year in year_range:
        # Define the parameters for the API request
        params = {
            "limit": 100,
            "yearFrom": year,
            "yearTo": year,
            "coo": coo,
            "coa": coa,
            "cf_type": "iso"
        }

        # Make the API request
        response = requests.get(url, params=params)

        # Check if the request was successful (status code 200)
        if response.status_code == 200:
            data = response.json()

            # Process and store data based on priority
            for item in data.get("items", []):
                key = (year, item['coo_name'], item['coa_name'])
                dec_level = item['dec_level']

                # Check if the current record has a higher priority
                if key not in highest_priority_records or decision_level_priority[dec_level] < decision_level_priority[highest_priority_records[key]['dec_level']]:
                    highest_priority_records[key] = item
        else:
            print(f"Failed to retrieve data for coa={coa}, year={year}. Status code: {response.status_code}")

# Insert the highest priority records into the database with geocoding
for key, record in highest_priority_records.items():
    coa_lat, coa_lng = get_coordinates(record['coa_name'], google_api_key)
    if coa_lat is None or coa_lng is None:
        continue  # Skip if coordinates are not found

    cursor.execute(f"""
        INSERT INTO asylum_decisions (
            year, coo_name, coa_name, procedure_type, dec_level, dec_recognized, dec_other, 
            dec_rejected, dec_closed, dec_total, coa_point
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, ST_PointFromText('POINT(%s %s)', 4326))
    """, (
        record['year'], record['coo_name'], record['coa_name'], record['procedure_type'], record['dec_level'],
        record['dec_recognized'], record['dec_other'], record['dec_rejected'],
        record['dec_closed'], record['dec_total'], coa_lng, coa_lat
    ))

# Commit the changes and close the connection
conn.commit()
cursor.close()
conn.close()

print("Data has been written to the PostgreSQL database with COA coordinates.")
