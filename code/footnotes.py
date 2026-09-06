import requests
import psycopg2

# Base API endpoint URL
url = "https://api.unhcr.org/population/v1/footnotes/"

# Define the parameters
coo = "UKR"
# Dictionary mapping of country names to their ISO codes
coa_countries = {
    "Austria": "AUT", "Germany": "DEU", "Italy": "ITA",
    "United Kingdom": "GBR", "Sweden": "SWE", "Switzerland": "SWI",
    "France": "FRA", "Spain": "ESP", "Netherlands": "NLD",
    "Belgium": "BEL", "Greece": "GRC", "Portugal": "PRT", "Poland": "POL"
}

# Database connection parameters
db_params = {
   "db params"
}

# Connect to the PostgreSQL database
conn = psycopg2.connect(**db_params)
cursor = conn.cursor()

# Table name
table_name = "footnotes"

# Create the table with the schema
create_table_query = f"""
CREATE TABLE IF NOT EXISTS {table_name} (
    year INTEGER,
    coo_name TEXT,
    coa_name TEXT,
    footnote TEXT,
    population_type TEXT
);
"""
cursor.execute(create_table_query)
conn.commit()

# Fetch data from the API
response = requests.get(url)
data = response.json()

# Process and insert relevant data into the database
for item in data.get("items", []):
    year = item.get("year", "").split(" - ")[0]  # Get the start year in case of a range
    coa_name = item.get("coa", "").strip()

    # Check if the COA country is in the list
    if coa_name in coa_countries:
        coo_name = item.get("coo", "").strip()
        footnote = item.get("footnote", "")
        population_type = item.get("population_type", "")

        insert_query = f"""
        INSERT INTO {table_name} (year, coo_name, coa_name, footnote, population_type)
        VALUES (%s, %s, %s, %s, %s)
        """
        cursor.execute(insert_query, (year, coo_name, coa_name, footnote, population_type))

# Commit the changes
conn.commit()

# Close the cursor and connection
cursor.close()
conn.close()

print("Data has been written to the PostgreSQL database.")
