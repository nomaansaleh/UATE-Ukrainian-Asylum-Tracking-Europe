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

# Connect to the database
conn = psycopg2.connect(**db_params)
cursor = conn.cursor()

# Google Geocoding API key
google_api_key = 'API KEY'

# Base API endpoint URL
url = "https://api.unhcr.org/population/v1/demographics/"

# Define the parameters
year_range = range(2013, 2023)
coo = "UKR"
coa_countries = ["AUT", "DEU", "ITA", "GBR", "SWE", "SWI", "FRA", "ESP", "NLD", "BEL", "GRC", "PRT", "POL"]

# Table name to check and potentially delete
table_name = "demographics"

# Check if the table exists, and delete it if it does
cursor.execute(sql.SQL("DROP TABLE IF EXISTS {}").format(sql.Identifier(table_name)))

# Create the new table with the specified schema including coordinates as a GEOMETRY(POINT, 4326) and age categories
create_table_query = f"""
CREATE TABLE {table_name} (
    year INTEGER,
    coo_name TEXT,
    coa_name TEXT,
    m_total INTEGER,
    f_total INTEGER,
    m_0_11 INTEGER,
    f_0_11 INTEGER,
    m_12_17 INTEGER,
    f_12_17 INTEGER,
    m_above_18 INTEGER,
    f_above_18 INTEGER,
    coa_point GEOMETRY(POINT, 4326)
);
"""
cursor.execute(create_table_query)
conn.commit()

# Loop through the coa_countries
for coa in coa_countries:
    for year in year_range:
        # Define the parameters for the API request
        params = {
            "limit": 10000,
            "yearFrom": year,
            "yearTo": year,
            "coo": coo,
            "coa": coa,
            "cf_type": "iso"
        }

        # Make the API request
        response = requests.get(url, params=params)

        if response.status_code == 200:
            data = response.json()

            # Process and store data
            for item in data.get("items", []):
                # Aggregating the data into age categories
                m_0_11 = int(item.get("m_0_4", 0)) + int(item.get("m_5_11", 0))
                f_0_11 = int(item.get("f_0_4", 0)) + int(item.get("f_5_11", 0))
                m_12_17 = int(item.get("m_12_17", 0))
                f_12_17 = int(item.get("f_12_17", 0))
                m_above_18 = int(item.get("m_18_59", 0)) + int(item.get("m_60", 0))
                f_above_18 = int(item.get("f_18_59", 0)) + int(item.get("f_60", 0))

                coa_name = item.get("coa_name", "")
                coa_lat, coa_lng = get_coordinates(coa_name, google_api_key)

                if coa_lat is not None and coa_lng is not None:
                    cursor.execute(sql.SQL("""
                        INSERT INTO {} (year, coo_name, coa_name, m_total, f_total, m_0_11, f_0_11, m_12_17, f_12_17, m_above_18, f_above_18, coa_point)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, ST_PointFromText('POINT(%s %s)', 4326))
                    """).format(sql.Identifier(table_name)),
                                   (year, item.get("coo_name", ""), coa_name,
                                    item.get("m_total", 0), item.get("f_total", 0), m_0_11, f_0_11, m_12_17, f_12_17, m_above_18, f_above_18, coa_lng, coa_lat))
        else:
            print(f"Failed to retrieve data for coa={coa}, year={year}. Status code: {response.status_code}")

# Commit the changes and close the connection
conn.commit()
cursor.close()
conn.close()

print("Data has been written to the PostgreSQL database with COA coordinates in GEOMETRY(POINT, 4326) format and age "
      "category breakdown.")
