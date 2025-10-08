# This file contains database-related functions
# including establishing a connection,
# inserting new rows into different tables,
# updating or deleting deleting,
# and querying the tables for info on users, events, scores, etc.

import os
import mysql.connector
import mysql.connector.pooling
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import logging
import sys

#logging.basicConfig(filename='output.log', level=logging.DEBUG,
#                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
stdout_handler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
stdout_handler.setFormatter(formatter)
logger.addHandler(stdout_handler)

DB_CONFIG = {
      'user': os.getenv("DB_USER"),
      'password': os.getenv("DB_PASSWORD"),
      'host': os.getenv("DB_HOST", "localhost"),
      'database': os.getenv("DB_NAME"),
      'port': int(os.getenv("DB_PORT", 3306)),
      'raise_on_warnings': True,
      'autocommit': True
}

# --- Create a pool at import time ---
POOL_SIZE = 6
_connection_pool = mysql.connector.pooling.MySQLConnectionPool(
    pool_name="fzdbot_pool",
    pool_size=POOL_SIZE,
    connection_timeout=10,  # seconds
    **DB_CONFIG
)

#def get_connection():
#    """Get a connection from the pool. Caller must close() it when done."""
#    try:
#        return _connection_pool.get_connection()
#    except mysql.connector.Error:
#        # re-initialize pool (should be rare)
#        print("GET_CONNECTION WARNING: needed to re-establish connection_pool")
#        global _connection_pool
#        _connection_pool = mysql.connector.pooling.MySQLConnectionPool(
#            pool_name="fzdbot_pool",
#            pool_size=POOL_SIZE,
#            connection_timeout=10,  # seconds
#            **DB_CONFIG
#        )
#        return _connection_pool.get_connection()

def get_connection_from_pool():
    """
    Context manager that safely checks out a connection from the pool,
    and returns it afterward (even if errors happen).
    Automatically rebuilds the pool if it breaks.
    """
    global _connection_pool
    conn = None
    try:
        conn = _connection_pool.get_connection()
        logger.info(f"[DB] Got connection from pool: id={id(conn)}, is_connected={conn.is_connected()}")
    except mysql.connector.Error:
        logger.warning("[DB CONNECTION] Have to re-establish pool...")
        # Rebuild pool if something is wrong (e.g. MySQL restarted...rare)
        _connection_pool = mysql.connector.pooling.MySQLConnectionPool(
            pool_name="fzdbot_pool",
            pool_size=POOL_SIZE,
            connection_timeout=10,  # seconds
            **DB_CONFIG
        )
        conn = _connection_pool.get_connection()
        logger.info(f"Got connection from pool: id={id(conn)}, is_connected={conn.is_connected()}")
    return conn

def release_connection(conn):
    """
    Close the connection (returns it to the pool).
    If the connection is broken, discard it.
    """
    try:
        conn.close()  # in pooled mode, this just releases it back
    except Exception as e:
        print(f"[DB CONNECTION] Warning: could not release connection: {e}")

@contextmanager
def get_db_connection():
    """
    Context manager for safely acquiring and releasing a DB connection.
    Rolls back on error and retries once if connection is lost.
    """
    conn = None
    try:
        conn = get_connection_from_pool()
         # Test connection quickly (cheap ping)
        conn.ping(reconnect=True, attempts=1, delay=0)

        yield conn  # hand off to the calling code

    except mysql.connector.Error as e:
        # Handle lost connection
        if conn:
            release_connection(conn)
            conn = None
            print("[DB] Connection rolled back and released")
        
        raise  # propagate error up to cog

    finally:
        if conn:
            release_connection(conn)


def execute_query(conn, query, params=None, fetch="all", isProc:bool = False):
    """
    Safely executes an SQL query with rollback on error.
    :conn: DB connection object
    :query: SQL query string
    :params: Optional tuple/list of parameters
    :fetch: "all", "one", or None (for INSERT/UPDATE/DELETE)
    :return: Query result or None if no result
    """
    cursor=None
    try:
        cursor = conn.cursor(dictionary=True)
        if isProc:
            cursor.callproc(query, params or ())
            if fetch == "all":
                for row in cursor.stored_results():
                    result = row.fetchall()
                    break
            elif fetch == "one":
                for row in cursor.stored_results():
                    result = row.fetchone()
                    break
            else:
                result = None
        else:
            cursor.execute(query, params or ())
            if fetch == "all":
                result = cursor.fetchall()
            elif fetch == "one":
                result = cursor.fetchone()
            else:
                result = None

        conn.commit()
        return result

    except Exception as e:
        conn.rollback()
        logger.error(f"[DB QUERY ERROR]: {e}\nQuery: {query}\nParams: {params}")
        raise

    finally:
        if cursor:
            cursor.close()

#def connect_to_database():
#    """ Establishes onnecttion to FZD database
#    """
#    config = {
#      'user': os.getenv("DB_USER"),
#      'password': os.getenv("DB_PASSWORD"),
#      'host': os.getenv("DB_HOST", "localhost"),
#      'database': os.getenv("DB_NAME"),
#      'port': int(os.getenv("DB_PORT", 3306)),
#      'raise_on_warnings': True 
#    }
#    try:
#        db = mysql.connector.connect(**config)
#        if db.is_connected():
#            # Ensure that any changes committed by other db connections are
#            # read in with each new query (e.g., if an event is started, then 
#            # Scoring commands will be able to 'see' the newly-committed event in the db)
#            cursor = db.cursor()
#            cursor.execute("SET SESSION TRANSACTION ISOLATION LEVEL READ COMMITTED")
#            print("✅ Connected to database")
#            return db
#    except mysql.connector.Error as err:
#        print(f"❌ Database connection failed: {err}")
#        return None

def get_event_types(db):
    """ Get event types and ids of recurring events from 'events' table
    """ 
    sql_gettypes = "SELECT id, name FROM events" # WHERE recurring = 1"
    eventtypes = execute_query(db, sql_gettypes, fetch="all")
    
    return eventtypes #[{'id': 7, 'name': 'Weekly Classic Mini'} . . .

def get_user_id(db, discord_id: str):
    """ Given a discord user id (discord_id), returns the database
        id of that user
    """
    sql_getuser = "SELECT id from users WHERE discord_user_id = %s"
    user = execute_query(db, sql_getuser, params=(discord_id,),  fetch="one")
    if user:
        return user['id']
    else:
        return None

#def _check_user_tag(db, display_name)
#    cursor = db.cursor(dictionary=True)
#    sql = "SELECT COUNT(1) FROM users WHERE unique_key = %s;"
#    cursor.execute(sql, (display_name) )
#    tag_exists = cursor.fetchone()
#     
#    return tag_exists

def add_new_user(db, discord_username, display_name=None) -> None:
    """ Adds new user to the database
    """ 
    #cursor = db.cursor(dictionary=True)
    
    # Assuming "discord_display_name" isn't required 
    sql_newuser="INSERT INTO users (tag, discord_user_id) VALUES (%s, %s);"

    if display_name is None: # Defaults to user's server display name 
        display_name = discord_username.nick[0:10]
    execute_query(db, sql_newuser, params=(display_name, discord_username.name), fetch=None)
    #cursor.execute(sql_newuser, (display_name, discord_username.name)) #, discord_username.name))
    #db.commit()

def modify_user_display_name(db, db_user_id, display_name) -> None:
    """ Modifies an existing user's display name in the database
    """
    #cursor = db.cursor(dictionary=True)

    sql_modifyuser="UPDATE users SET tag = %s WHERE id = %s;"
    execute_query(db, sql_modifyuser, params=(display_name, db_user_id), fetch=None)
    #cursor.execute(sql_modifyuser, (display_name, db_user_id))
    #db.commit()

def create_event(db, event, duration: int = 2) -> None:
    """ Inserts new event into the 'events_scheduled' database
        duration is optional variable to set how long the event window is (2 hours by default)
    """
    now = datetime.now(timezone.utc) #now.strftime('%Y-%m-%d %H:%M:%S')
    endtime =  now + timedelta(hours=duration)
    tformat = '%Y-%m-%d %H:%M:%S'
    
    #cursor = db.cursor(dictionary=True)
    sql_addevent = "INSERT INTO events_scheduled (event_id, utc_start_dt, utc_end_dt) VALUES (%s, %s, %s);"
    #cursor.execute(sql_addevent, (event['id'], now.strftime(tformat), endtime.strftime(tformat)) )
    #db.commit()
    execute_query(db, sql_addevent, params=(event['id'], now.strftime(tformat), endtime.strftime(tformat)), fetch=None)

def check_for_active_event(db, hours_from_now: int = 0):
    """ Checks database event times start and end times to see if
        event is active right now, returns dict with name and id
    """
    active_event = {'name':"NULL",'id':0} # Assume no match

    #cursor = db.cursor(dictionary=True)
    sql_getevent="""SELECT es.id, e.name, es.utc_start_dt, es.utc_end_dt 
                    FROM events_scheduled es
                    JOIN events e ON e.id = es.event_id
                    WHERE DATE_ADD(UTC_TIMESTAMP(), INTERVAL %s HOUR) 
                          BETWEEN utc_start_dt AND utc_end_dt;"""
    
    #cursor.execute(sql_getevent, (hours_from_now,) )
    #eventmatch = cursor.fetchone()
    eventmatch = execute_query(db, sql_getevent, params=(hours_from_now,), fetch="one") 
    if eventmatch:
        active_event['name'] = eventmatch['name']
        active_event['id']   = eventmatch['id']

    return active_event

def submit_score(db, dataentry) -> None:
    """ Executes sql query command to insert data to database
        db = database connection object
        dataentry = [ user_id, scheduled_event_id, score ] - all integers
    """
    #cursor = db.cursor(dictionary=True)
    #sql_newrow="INSERT INTO event_result_points (scheduled_event_id, user_id, score) VALUES (%s, %s, %s);"
    sql_newrow="sp_insert_score"
    #cursor.execute(sql_newrow, dataentry)
    #db.commit()
    execute_query(db, sql_newrow, params=dataentry, fetch=None, isProc=True)

def edit_score(db, dataentry) -> None:
    """ Executes sql query command to insert data to database
        db = database connection object
        dataentry = [ newscore, id ] for modifying score, 
                    all integer values
    """
    #cursor = db.cursor(dictionary=True)
    sql_updaterow="UPDATE event_result_points SET score = %s WHERE id = %s;" 
    #cursor.execute(sql_updaterow, dataentry)
    #db.commit()
    execute_query(db, sql_updaterow, params=dataentry, fetch=None)

def delete_score(db, dataentry) -> None:
    """ Executes sql query command to insert data to database
        db = database connection object
        dataentry = [ id ] for deleting score
                    all integer values
    """
    #cursor = db.cursor(dictionary=True)
    sql_deleterow="DELETE FROM event_result_points WHERE id = %s;"
    #cursor.execute(sql_deleterow, dataentry)
    #db.commit()
    execute_query(db, sql_deleterow, params=dataentry, fetch=None)

def get_user_scores(db, user_name) -> list[dict[str,str]]:
    """ Query the database for scores of active event of a given user
        Returns all values as strings for autocomplete bot feature
    """
    active_event =  check_for_active_event(db)
    if (active_event['name'] == "NULL"):
        return [{'score':"NO CURRENT EVENT", 'id':'-999'}]
    db_user_id = get_user_id(db, user_name)
    
    #cursor = db.cursor(dictionary=True)
    sql_getscores = """SELECT CAST(score AS CHAR) AS score, 
                              CAST(id AS CHAR) AS id
                       FROM event_result_points 
                       WHERE user_id = %s AND scheduled_event_id = %s 
                       ORDER BY id ASC;"""
    #cursor.execute(sql_getscores, (db_user_id, active_event['id']))
    #scoresdict = cursor.fetchall()  #[{'score': 667, 'id': 472}, ...]
    scoresdict =  execute_query(db, sql_getscores, params=(db_user_id, active_event['id']), fetch="all")    

    if not scoresdict:
        return [{'score':"NO USER SCORES FOUND", 'id':'-999'}]

    return scoresdict

def get_latest_event(db, event_id=None):
    """ Get most recent event, return a dict containing the unique id, 
        name of event, and start date of the event
        OPTIONAL: event_id to find latest of a specific event
    """
    #cursor = db.cursor(dictionary=True)
    sql_getevent="""SELECT es.id, e.name, es.utc_start_dt, es.utc_end_dt, es.event_id
                    FROM events_scheduled es
                    JOIN events e ON e.id = es.event_id
                    WHERE utc_start_dt =
                        (SELECT MAX(utc_start_dt) FROM events_scheduled 
                         WHERE utc_start_dt < UTC_TIMESTAMP())"""
    #if event_id is None:
        #cursor.execute(sql_getevent)
    #    selectedevent = execute_query(sql_getevent, fetch="one")
    #else:
    params=None
    if event_id is not None:
        sql_getevent = sql_getevent.replace("())", "() AND event_id = %s)")
        params=(event_id,)
        #cursor.execute(sql_getevent, [event_id])

    icoreboard = []
    selectedevent = execute_query(db, sql_getevent, params=params, fetch="one")
    
    #  selectedevent = cursor.fetchone()
    
    return  selectedevent

def get_event_scoreboard(db, event_type=None, getQualified: bool = False):
    """ Query the FZD database for all scores of a given event,
        defined by scheduled_event_id.

        Returns an ordered list of dicts with 'player': str and 'score': Decimal 
        as well as the eventinfo (from get_latest_event function)
    """
    #qual_str = ""
    #if getQualified#:
    #    qual_str="1 AS is_qualified,"
    sql_getscoreboard="sp_show_scoreboard"
    #sql_getscoreboard=(
    #"""SELECT player, score,
    #           CASE WHEN is_qualified AND is_participating 
    #           THEN 1 ELSE 0 END as is_qualified
    #   FROM (
    #       SELECT
    #            COALESCE(u.tag, u.discord_user_id) AS player, 
    #            SUM(erp.score) AS score,
    #            1 as is_qualified,
    #            ew.is_participating
 # 	   FROM event_result_points erp 
 # 	   JOIN users u ON u.id = erp.user_id
 # 	   JOIN events_whitelist ew ON ew.user_id = u.id
 #          JOIN events e ON e.id = ew.event_id
 #          JOIN events_scheduled es ON es.event_id = e.id
 #          WHERE erp.scheduled_event_id = %s
 #          AND now() < es.utc_start_dt
 #          GROUP BY player, is_participating
#
#           UNION
#
#           SELECT
#               COALESCE(u.tag, u.discord_user_id) AS player, 
#               SUM(erp.score) AS score,
#               0 as is_qualified,
#               0 as is_participating
#           FROM event_result_points erp 
#           JOIN users u ON u.id = erp.user_id
#           WHERE erp.scheduled_event_id = %s
#           AND erp.user_id NOT IN (
#               SELECT user_id 
#               FROM events_whitelist ew
#               JOIN events e ON e.id = ew.event_id
#               JOIN events_scheduled es ON es.event_id = e.id
#               WHERE now() < es.utc_start_dt
#           )
#       GROUP BY player, is_participating
#       ORDER BY score DESC
#       ) event_results;"""
#    )
    #f"""SELECT COALESCE(u.tag, u.discord_display_name, u.discord_user_id) AS player, 
    #   {qual_str}
    #   SUM(erp.score) AS score 
    #   FROM  
    #     event_result_points erp 
    #   JOIN 
    #     users u ON u.id = erp.user_id 
    #   WHERE scheduled_event_id = %s 
    #   GROUP BY player 
    #   ORDER BY score DESC;"""
    #)
    if event_type is None:
        eventinfo=get_latest_event(db)
    else:
        eventinfo=get_latest_event(db, event_id=int(event_type))
    #cursor = db.cursor(dictionary=True)

    # Check there's an event to display
    if not eventinfo:
        return None, None
   
    #cursor.execute(sql_getscoreboard, [eventinfo['id']]) 
    #allscores = cursor.fetchall() #[{'player': 'Angelo', 'score': Decimal('1140')}...]

    allscores = execute_query(db, sql_getscoreboard, params=(eventinfo['id'],), isProc=True)
    
    # strip off is_qualified results if we're not viewing a qualifier event
    valid_qual_events = [8,9,10,11,12,13] # MM, Thu FZD, Fri FZD, EAD, CC, APAC
    if not eventinfo['event_id'] in valid_qual_events: 
        for d in allscores:
            d.pop("is_qualified",None)

    return eventinfo, allscores

