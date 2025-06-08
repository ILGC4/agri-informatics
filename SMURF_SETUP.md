# SMURF - Sugarcane Management and Utility Resource Framework

## Overview
SMURF is a sugarcane mill management and monitoring platform integrating satellite data, weather APIs, and PostgreSQL for farm analytics and alerting. There are 3 personas that this platform targets --mill manager, farmer and field officer. We have implemented field officer persona and have designed mock ups for the farmer persona.

---

## Server Access
- **SSH:**
  ```
  ssh smurfs@10.1.45.56
  ```
  **Password:** `smurfs123`

  Note that you need to be connected to Plaksha network for the server to work.

---

## Conda Environment
- **Environment location:**  `miniforge3/envs/smurfs`
- **Activate:**
  ```
  conda activate smurfs
  ```

---

## Database Connection
- **Host:** `localhost`
- **Port:** `5432`
- **Database:** `smurf` (PostGIS enabled)
- **User:** `smurfs`
- **Password:** `smurfs123`
- **Login with psql:**
  ```
  psql -U smurfs -d smurf
  ```
- **View tables:**
  After logging in, use:
  ```
  \dt
  ```
  to list all tables.
- **To quit:**  
  After logging in, use:
  ```
  \q
  ```
  to quit the database.

---

## Repositories

### [agri-info (Backend)](https://github.com/SMURFTool/agri-informatics)

- **Overview:**
  The backend is a FastAPI application that provides RESTful APIs for satellite data collection, weather-based analytics, farm health alerts, and geospatial database access. It integrates with external APIs (Planet, OpenWeather, Google Earth Engine) and a PostgreSQL/PostGIS database. All core data processing and business logic for the SMURF platform is implemented here.
- **Clone:**
  ```
  git clone https://github.com/SMURFTool/agri-informatics.git
  ```
- **Install dependencies:**
  - For standard requirements:
    ```
    pip install -r requirements.txt
    ```
  - For full/detailed requirements:
    ```
    pip install -r detailed_requirements.txt
    ```
  - Use `requirements.txt` for basic setup, or `detailed_requirements.txt` for all optional/extra dependencies.
- **To run the backend:**
  1. Change to the agri-info directory:
     ```
     cd agri-info
     ```
  2. Run:
     ```
     python3 api_main.py
     ```
- **API Keys:**
  The `api_key` directory in `agri-info/` stores all API key files required for backend operation.
  
  > **Note:** API keys have been removed from the repositories for security reasons. The variable names and structure are present; kindly generate your own API keys and add them as described below.

  **Earth Engine**
  - **Service Account:** Place your Earth Engine service account JSON in `agri-info/api_key/`.
  - **Important:**  
    If you generate a new service account JSON, you must update the filename/path in the following files and lines:
    - `api_main.py`, line 167
    - `Utils/satellite_gee.py`, line 527
    - `Utils/update_farm_alerts_db.py`, line 1033  
    Replace all references to `ee-chaitanyamodi-6874ede8f64c.json` with your new JSON filename.

  **Weather API (OpenWeather)**
  - **API Key:** Place your OpenWeather API key JSON in `agri-info/api_key/openweather.json`
  - **Get your API key:** [OpenWeather API Key Registration](https://home.openweathermap.org/api_keys)
  - **File format:**
    ```json
    { "OPENWEATHER_API_KEY": "<your_api_key_here>" }
    ```

  **Planet API**
  - **API Key:** Place your Planet API key JSON in `agri-info/api_key/planet.json`
  - **Get your API key:** [Planet API Key Registration](https://www.planet.com/account/#/)
  - **File format:**
    ```json
    { "API_KEY": "<your_planet_api_key_here>" }
    ```

- **Cron jobs:**
  Cron jobs have been removed currently. You can add them again by running the provided `.sh` shell scripts in the `cron_job/` directory. For example:
  ```
  cd cron_job
  ./cron_setup.sh
  ```
  See the `cron_job/` directory for setup scripts and further documentation.

- **Database:**
  The backend uses a PostgreSQL database with the PostGIS extension for geospatial data. The database contains four main tables:
  - `farm_data`: Stores individual farm plot information, boundaries, crop details, and health metrics.
  - `village_data`: Contains village boundaries, centroids, and field officer assignments.
  - `field_officer_credentials`: Manages authentication and user info for field officers.
  - `satellite_images`: Tracks metadata for satellite imagery used in analysis.

  All geometry data uses the WGS84 coordinate system (SRID 4326). The schema is designed for efficient geospatial queries and agricultural monitoring, supporting features like NDVI, waterlogging, and harvest readiness.

  For more details on the schema, table relationships, and utility scripts, see `agri-info/Backend_Documentation/database_documentation.md`.

- **Detailed Documentation:**
You can find the detailed documentation of the entire backend, including the database, in agri-info/Backend_Documentation/

### [react_smurf (Frontend)](https://github.com/SMURFTool/react_smurf)

- **Overview:**
  The frontend is a Next.js (React) application providing a modern, role-based dashboard for field officers, mill managers, and farmers. It integrates with the FastAPI backend for real-time analytics, farm health alerts, and geospatial data visualization. Only the field officer persona is fully implemented.
- **Clone:**
  ```
  git clone https://github.com/SMURFTool/react_smurf.git
  ```
- **Install dependencies:**
  ```
  cd react_smurf
  npm install
  ```
- **Run development server:**
  ```
  npm run dev
  ```
- **Access:**
  Open [http://localhost:3000](http://localhost:3000) in your browser.
  
  To view the current work, log in as a field officer. Example credentials (others can be found in the `field_officer_credentials` table in the database):
  - **Field officer's name:** Chaitanya
  - **Username:** chaitanya123
  - **Password:** chaitanya123

> **Note:** API key have been removed from the repository for security reasons. The Google Maps API key required for the frontend must be placed in the `.env` file inside the `/react_smurf` directory. Please note that this is separate from the Earth Engine API key used in the backend. Please generate your own Google Maps API key and add it to the `.env` file as described in the frontend documentation.

For more details on the frontend, refer to `react_smurf/README.md`.

---
## How to Run the Project:
1. **SSH into the server and activate the conda environment.**
2. **Start the backend FastAPI server:**
3. **Start the frontend Next.js server.**
4. **Ensure the database credentials are configured.**

---

## Useful Links
- [agri-info GitHub](https://github.com/SMURFTool/agri-informatics)
- [react_smurf GitHub](https://github.com/SMURFTool/react_smurf)
- [Earth Engine Documentation](https://developers.google.com/earth-engine)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
