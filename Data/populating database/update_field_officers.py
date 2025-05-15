import psycopg2
import random
import string

# --- Database Connection Details (Update if different from populate_data.py) ---
DB_NAME = "smurf"
DB_USER = "clumsysmurf"
DB_PASSWORD = "clumsysmurf"
DB_HOST = "localhost"
DB_PORT = "5432"

def generate_random_password(length=10):
    """Generates a random alphanumeric password."""
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for i in range(length))

def main():
    conn = None
    cur = None

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

        # 1. Add 21 new field officer entries
        print("Adding 21 new field officer entries...")
        
        # Get the current max field_officer_id to start numbering new officers
        cur.execute("SELECT MAX(field_officer_id) FROM public.field_officer_credentials;")
        max_id_result = cur.fetchone()
        start_id = 0
        if max_id_result and max_id_result[0] is not None:
            start_id = max_id_result[0]
        
        officers_added_count = 0
        for i in range(1, 22): # Add 21 officers
            officer_number = start_id + i
            name = f"Field Officer {officer_number}"
            username = f"fo_{officer_number}_user" # Unique username
            password = generate_random_password()

            try:
                cur.execute("""
                    INSERT INTO public.field_officer_credentials (name, username, password)
                    VALUES (%s, %s, %s);
                """, (name, username, password))
                officers_added_count +=1
            except psycopg2.IntegrityError as e:
                print(f"Could not insert officer {name} (username: {username}). It might already exist or violate a constraint: {e}")
                conn.rollback() # Rollback the failed insert
                cur = conn.cursor() # Re-initialize cursor
            except Exception as e:
                print(f"An error occurred while inserting officer {name}: {e}")
                conn.rollback()
                cur = conn.cursor()


        if officers_added_count > 0:
            print(f"Successfully added {officers_added_count} new field officers.")
        else:
            print("No new field officers were added (they might exist already or an error occurred).")

        # 2. Add foreign key constraint to village_data table
        fk_constraint_name = "fk_village_field_officer"
        
        # First, try to drop the constraint if it exists, to make the script idempotent
        try:
            cur.execute(f"ALTER TABLE public.village_data DROP CONSTRAINT IF EXISTS {fk_constraint_name};")
            print(f"Attempted to drop existing constraint '{fk_constraint_name}' (if it existed).")
        except psycopg2.Error as e:
            # This might happen if the constraint is in use or other issues.
            # For simple cases, "IF EXISTS" handles it. If it's more complex, manual intervention might be needed.
            print(f"Notice: Could not drop constraint '{fk_constraint_name}' (it might not exist or be in use): {e}")
            conn.rollback() # Rollback before trying to add
            cur = conn.cursor()


        print(f"Adding foreign key constraint '{fk_constraint_name}' to public.village_data...")
        try:
            cur.execute(f"""
                ALTER TABLE public.village_data
                ADD CONSTRAINT {fk_constraint_name}
                FOREIGN KEY (field_officer_id)
                REFERENCES public.field_officer_credentials(field_officer_id);
            """)
            print(f"Successfully added foreign key constraint '{fk_constraint_name}'.")
        except psycopg2.Error as e:
            # Check if the error is because the constraint already exists
            if "already exists" in str(e).lower():
                 print(f"Constraint '{fk_constraint_name}' already exists.")
            # Check if the error is due to invalid foreign key values
            elif "violates foreign key constraint" in str(e).lower() or "is not present in table" in str(e).lower():
                print(f"Error: Could not add foreign key. Some field_officer_id values in village_data do not exist in field_officer_credentials.")
                print(f"Details: {e}")
            else:
                print(f"Error adding foreign key constraint '{fk_constraint_name}': {e}")
            conn.rollback() # Rollback if alter table fails
            cur = conn.cursor()


        conn.commit()
        print("\\nField officer update and foreign key setup completed.")

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