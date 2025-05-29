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

## Earth Engine
- **Service Account:**  Place your Earth Engine service account JSON in `agri-info/api_key/`
- **Earth Engine ID:**  (Add your service account email or ID here)

## Weather API (OpenWeather)
- **API Key:** Place your OpenWeather API key JSON in `agri-info/api_key/openweather.json`
- **Get your API key:** [OpenWeather API Key Registration](https://home.openweathermap.org/api_keys)
- **File format:**
  ```json
  { "OPENWEATHER_API_KEY": "<your_api_key_here>" }
  ```

## Planet API
- **API Key:** Place your Planet API key JSON in `agri-info/api_key/planet.json`
- **Get your API key:** [Planet API Key Registration](https://www.planet.com/account/#/)
- **File format:**
  ```json
  { "API_KEY": "<your_planet_api_key_here>" }
  ```

---

## Repositories

### [agri-info (Backend)](https://github.com/SMURFTool/agri-informatics)

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
- **Cron jobs:**
  To add or manage scheduled tasks, run the provided `.sh` shell scripts in the `cron_job/` directory. For example:
  ```
  cd cron_job
  ./cron_setup.sh
  ```
  See the `cron_job/` directory for setup scripts and further documentation.

- **Detailed Documentation:**
You can find the detailed documentation of the entire backend in agri-info/Backend Documentation/

### [react_smurf (Frontend)](https://github.com/SMURFTool/react_smurf)

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

---
## How to Run
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
