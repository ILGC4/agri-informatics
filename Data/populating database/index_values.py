import psycopg2
import random

# --- Database Connection Details (Update if different) ---
DB_NAME = "smurf"
DB_USER = "clumsysmurf"
DB_PASSWORD = "clumsysmurf"
DB_HOST = "localhost"
DB_PORT = "5432"

# --- Weighted choices for status values ---
# Values: 1, 2, 3
# Probabilities: 0.25 for 1, 0.50 for 2, 0.25 for 3
STATUS_VALUES = [1, 2, 3]
STATUS_WEIGHTS = [0.25, 0.50, 0.25]

def get_random_status_value():
    """Returns a random status value (1, 2, or 3) based on specified weights."""
    return random.choices(STATUS_VALUES, STATUS_WEIGHTS, k=1)[0]

def main():
    conn = None
    cur = None
    updated_rows_count = 0

    try:
        # Connect to the PostgreSQL database
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        cur = conn.cursor()

        # 1. Get all plot_numbers from farm_data
        cur.execute("SELECT plot_number FROM public.farm_data;")
        plot_numbers = cur.fetchall()

        if not plot_numbers:
            print("No farms found in farm_data table. Nothing to update.")
            return

        print(f"Found {len(plot_numbers)} farms to update.")

        # 2. Update each farm with random status values
        for row in plot_numbers:
            plot_number = row[0]
            
            health_value = get_random_status_value()
            harvest_readiness_value = get_random_status_value()
            waterlogging_value = get_random_status_value()

            try:
                cur.execute("""
                    UPDATE public.farm_data
                    SET health = %s,
                        harvest_readiness = %s,
                        waterlogging = %s
                    WHERE plot_number = %s;
                """, (health_value, harvest_readiness_value, waterlogging_value, plot_number))
                updated_rows_count += 1
                if updated_rows_count % 100 == 0: # Print progress every 100 rows
                    print(f"Updated {updated_rows_count} farms...")
            except Exception as e:
                print(f"Error updating plot {plot_number}: {e}")
                conn.rollback() # Rollback this specific update if needed, or handle more globally
                cur = conn.cursor() # Re-initialize cursor if rollback occurred
        
        conn.commit()
        print(f"\\nSuccessfully updated {updated_rows_count} farms with random status values.")

    except (Exception, psycopg2.Error) as error:
        print(f"Error connecting to or working with PostgreSQL: {error}")
        if conn:
            conn.rollback()
    finally:
        # Close the database connection
        if cur:
            cur.close()
        if conn:
            conn.close()
            print("PostgreSQL connection is closed.")

if __name__ == "__main__":
    main()