from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError, ProgrammingError
from urllib.parse import urlparse
import logging

def ensure_database_exists(db_uri, logger):
    """Checks if the database exists and creates it if not."""
    try:
        parsed_uri = urlparse(db_uri)
        db_name = parsed_uri.path[1:]  # Get db name from /dbname
        if not db_name:
            logger.error("Database name could not be parsed from URI.")
            return False

        # Credentials and connection details (handle potential None values)
        db_user = parsed_uri.username or 'postgres'  # Default to 'postgres' if not specified
        db_password = parsed_uri.password or ''
        db_host = parsed_uri.hostname or 'localhost'
        db_port = parsed_uri.port or 5432

        # Construct URI for the default 'postgres' database (or template1)
        default_db_uri = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/postgres"
        logger.info(f"Connecting to default database at {db_host}:{db_port} to check/create '{db_name}'...")

        # Connect to the default database with autocommit
        engine = create_engine(default_db_uri, isolation_level='AUTOCOMMIT')

        with engine.connect() as connection:
            # Check if the target database exists
            # Use parameterized query for safety
            check_sql = text("SELECT 1 FROM pg_database WHERE datname = :database_name")
            result = connection.execute(check_sql, {"database_name": db_name})
            database_exists = result.scalar() == 1

            if not database_exists:
                logger.info(f"Database '{db_name}' does not exist. Attempting to create...")
                # Create the database (ensure user has CREATE DATABASE privileges)
                create_sql = text(f'CREATE DATABASE "{db_name}"')  # Quote db name
                connection.execute(create_sql)
                logger.info(f"Database '{db_name}' created successfully.")
            else:
                logger.info(f"Database '{db_name}' already exists.")
        return True  # Indicate success or existing database

    except OperationalError as e:
        # Handle specific connection errors (e.g., wrong password, host unreachable)
        logger.error(f"OperationalError: Could not connect to PostgreSQL server or create database '{db_name}'. Check connection details and permissions. Error: {e}")
        return False  # Indicate failure
    except ProgrammingError as e:
        # Handle errors like permission denied for CREATE DATABASE
        logger.error(f"ProgrammingError: Could not create database '{db_name}'. User might lack CREATE DATABASE privileges. Error: {e}")
        return False  # Indicate failure
    except Exception as e:
        # Catch other potential exceptions
        logger.error(f"An unexpected error occurred during database check/creation for '{db_name}': {e}")
        return False  # Indicate failure
