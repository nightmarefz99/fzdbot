import os
import mysql.connector
from datetime import datetime, timedelta, timezone

def connect_to_database():
    """ Establishes onnecttion to FZD database
    """
    config = {
      'user': os.getenv("DB_USER"),
      'password': os.getenv("DB_PASSWORD"),
      'host': os.getenv("DB_HOST", "localhost"),
      'database': os.getenv("DB_NAME"),
      'port': int(os.getenv("DB_PORT", 3306)),
      'raise_on_warnings': True 
    }
    try:
        db = mysql.connector.connect(**config)
        if db.is_connected():
            print("✅ Connected to database")
            return db
    except mysql.connector.Error as err:
        print(f"❌ Database connection failed: {err}")
        return None

def get_event_types(db):
    """ Get event types and ids of recurring events from 'events' table
    """ 
    cursor = db.cursor(dictionary=True) # Pass back results as dict
    sql_gettypes = "SELECT id, name FROM events WHERE recurring = 1"
    cursor.execute(sql_gettypes)
    eventtypes = cursor.fetchall()
    
    return eventtypes #[{'id': 7, 'name': 'Weekly Classic Mini'} . . .

def get_user_id(db, discord_id: str):
    """ Given a discord user id (discord_id), returns the database
        id of that user
    """
    cursor = db.cursor(dictionary=True) 
    sql_getuser = "SELECT id from users WHERE discord_user_id = %s"
    cursor.execute(sql_getuser, [discord_id])
    user = cursor.fetchone()
    if user:
        return user['id']
    else:
        return None

def add_new_user(db, discord_username, display_name=None) -> None:
    """ Adds new user to the database
    """ 
    cursor = db.cursor(dictionary=True)
    
    # Assuming "discord_display_name" isn't required 
    sql_newuser="INSERT INTO users (tag, discord_user_id) VALUES (%s, %s);"

    if display_name is None: # Defaults to user's server display name 
        display_name = discord_username.nick[0:10]

    cursor.execute(sql_newuser, (display_name, discord_username.name)) #, discord_username.name))
    db.commit()

def modify_user_display_name(db, db_user_id, display_name) -> None:
    """ Modifies an existing user's display name in the database
    """
    cursor = db.cursor(dictionary=True)

    sql_modifyuser="UPDATE users SET tag = %s WHERE id = %s;"
    cursor.execute(sql_modifyuser, (display_name, db_user_id))
    db.commit()

def create_event(db, event) -> None:
    """ Inserts new event into the 'events_scheduled' database
    """
    now = datetime.now(timezone.utc) #now.strftime('%Y-%m-%d %H:%M:%S')
    endtime =  now + timedelta(hours=2)
    tformat = '%Y-%m-%d %H:%M:%S'
    
    cursor = db.cursor(dictionary=True)
    sql_addevent = "INSERT INTO events_scheduled (event_id, utc_start_dt, utc_end_dt) VALUES (%s, %s, %s);"
    cursor.execute(sql_addevent, (event['id'], now.strftime(tformat), endtime.strftime(tformat)) )
    db.commit()

def check_for_active_event(db):
    """ Checks database event times start and end times to see if
        event is active right now, returns dict with name and id
    """
    active_event = {'name':"NULL",'id':0} # Assume no match

    cursor = db.cursor(dictionary=True)

    sql_getevent="""SELECT es.id, e.name, es.utc_start_dt, es.utc_end_dt 
                    FROM events_scheduled es
                    JOIN events e ON e.id = es.event_id
                    WHERE UTC_TIMESTAMP() BETWEEN utc_start_dt AND utc_end_dt;"""
    cursor.execute(sql_getevent)
    eventmatch = cursor.fetchone()
    if eventmatch:
        active_event['name'] = eventmatch['name']
        active_event['id']   = eventmatch['id']

    return active_event

def submit_score(db, dataentry) -> None:
    """ Executes sql query command to insert data to database
        db = database connection object
        dataentry = [ scheduled_event_id, user_id, lineup_id, score ] - all integers
    """
    cursor = db.cursor(dictionary=True)
    sql_newrow="INSERT INTO event_result_points (scheduled_event_id, user_id, score) VALUES (%s, %s, %s);"
    cursor.execute(sql_newrow, dataentry)
    db.commit()

def edit_score(db, dataentry) -> None:
    """ Executes sql query command to insert data to database
        db = database connection object
        dataentry = [ newscore, id ] for modifying score, 
                    all integer values
        delete = Optional bool to delete score
    """
    cursor = db.cursor(dictionary=True)
    sql_updaterow="UPDATE event_result_points SET score = %s WHERE id = %s;" 
    cursor.execute(sql_updaterow, dataentry)
    
    db.commit()

def delete_score(db, dataentry) -> None:
    """ Executes sql query command to insert data to database
        db = database connection object
        dataentry = [ id ] for deleting score
                    all integer values
        delete = Optional bool to delete score
    """
    cursor = db.cursor(dictionary=True)
    sql_deleterow="DELETE FROM event_result_points WHERE id = %s;"
    cursor.execute(sql_deleterow, dataentry)

    db.commit()

def get_user_scores(db, user_name) -> list[dict[str,str]]:
    """ Query the database for scores of active event of a given user
        Returns scoresmatch (list[str]) and idmatch (list[str])
    """
    active_event =  check_for_active_event(db)
    if (active_event['name'] == "NULL"):
        return [{'score':"NO CURRENT EVENT", 'id':'-999'}]
    db_user_id = get_user_id(db, user_name)
    
    cursor = db.cursor(dictionary=True)
    sql_getscores = """SELECT CAST(score AS CHAR) AS score, 
                              CAST(id AS CHAR) AS id
                       FROM event_result_points 
                       WHERE user_id = %s AND scheduled_event_id = %s 
                       ORDER BY id ASC;"""
    cursor.execute(sql_getscores, (db_user_id, active_event['id']))
    scoresdict = cursor.fetchall()  #[{'score': 667, 'id': 472}, ...]
    
    if not scoresdict:
        return [{'score':"NO USER SCORES FOUND", 'id':'-999'}]

    return scoresdict

def get_latest_event(db, event_id=None):
    """ Get most recent event, return a dict containing the unique id, 
        name of event, and start date of the event
        OPTIONAL: event_id to find latest of a specific event
    """
    cursor = db.cursor(dictionary=True)
    sql_getevent="""SELECT es.id, e.name, es.utc_start_dt, es.utc_end_dt 
                    FROM events_scheduled es
                    JOIN events e ON e.id = es.event_id
                    WHERE utc_start_dt =
                        (SELECT MAX(utc_start_dt) FROM events_scheduled 
                         WHERE utc_start_dt < UTC_TIMESTAMP())"""
    if event_id is None:
        cursor.execute(sql_getevent)
    else:
        sql_getevent = sql_getevent.replace("())", "() AND event_id = %s)")
        cursor.execute(sql_getevent, [event_id])
    
    selectedevent = cursor.fetchone()
    
    return  selectedevent

def get_event_scoreboard(db, event_type=None):
    """ Query the FZD database for all scores of a given event,
        defined by scheduled_event_id.

        Returns an ordered list of dicts with 'player': str and 'score': Decimal 
        as well as the eventinfo (from get_latest_event function)
    """

    sql_getscoreboard=(
    """SELECT COALESCE(u.tag, u.discord_display_name, u.discord_user_id) AS player, 
       SUM(erp.score) AS score 
       FROM  
         event_result_points erp 
       JOIN 
         users u ON u.id = erp.user_id 
       WHERE scheduled_event_id = %s 
       GROUP BY player 
       ORDER BY score DESC;"""
    )
    if event_type is None:
        eventinfo=get_latest_event(db)
    else:
        eventinfo=get_latest_event(db,event_id=event_type)
    cursor = db.cursor(dictionary=True)

    # Check there's an event to display
    if not eventinfo:
        return None, None
   
    cursor.execute(sql_getscoreboard, [eventinfo['id']]) 
    allscores = cursor.fetchall() #[{'player': 'Angelo', 'score': Decimal('1140')}...]
 
    return eventinfo, allscores

