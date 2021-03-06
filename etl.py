import os
import glob
import psycopg2
import pandas as pd
from sql_queries import *


def process_song_file(cur, filepath):
    # open song file
    df = pd.read_json(filepath, lines=True)

    # insert song record
    song_data = df[["song_id", "title", "artist_id", "year", "duration"]].values[0].tolist()
    cur.execute(song_table_insert, song_data)
    
    # insert artist record
    artist_data = df[["artist_id", "artist_name", "artist_location", "artist_latitude", "artist_longitude"]].values[
        0].tolist()
    cur.execute(artist_table_insert, artist_data)


def process_log_file(cur, filepath):
    # open log file
    logsdf = pd.read_json(filepath, lines=True)

    # filter by NextSong action
    # df = 
    nextsongdf = logsdf[(logsdf['page'] == 'NextSong')]

    # convert timestamp column to datetime
    t = pd.to_datetime(nextsongdf['ts'], unit='ms')
    
    # insert time data records
    time_data = list((t, t.dt.hour, t.dt.day, t.dt.weekofyear, t.dt.month, t.dt.year, t.dt.weekday))
    column_labels = list(('start_time', 'hour', 'day', 'week', 'month', 'year', 'weekday'))
    time_df = pd.DataFrame.from_dict(dict(zip(column_labels, time_data)))

    for i, row in time_df.iterrows():
        cur.execute(time_table_insert, list(row))

    # load user table
    user_df = nextsongdf[["userId", "firstName", "lastName", "gender", "level"]]

    # insert user records
    for i, row in user_df.iterrows():
        cur.execute(user_table_insert, row)
    
    # insert songplay records
    nextsongdf = nextsongdf.astype({"ts": 'datetime64[ns]'})
    # for index, row in df.iterrows():
    for index, row in nextsongdf.iterrows():    
        # get songid and artistid from song and artist tables
        cur.execute(song_select, (row.song, row.artist, row.length))
        results = cur.fetchone()
        
        if results:
            songid, artistid = results
        else:
            songid, artistid = None, None

        # insert songplay record
        songplay_data = (index, row.ts, row.userId, row.level, songid, artistid, row.sessionId, \
                         row.location, row.userAgent)
        cur.execute(songplay_table_insert, songplay_data)


def process_data(cur, conn, filepath, func):
    # get all files matching extension from directory
    all_files = []
    for root, dirs, files in os.walk(filepath):
        files = glob.glob(os.path.join(root,'*.json'))
        for f in files :
            all_files.append(os.path.abspath(f))

    # get total number of files found
    num_files = len(all_files)
    print('{} files found in {}'.format(num_files, filepath))

    # iterate over files and process
    for i, datafile in enumerate(all_files, 1):
        func(cur, datafile)
        conn.commit()
        print('{}/{} files processed.'.format(i, num_files))

def main():
    try:
        conn = psycopg2.connect("host=127.0.0.1 dbname=sparkifydb user=student password=student")
    except Exception as error:
        print ("Oops! An exception has occured  in connection:", error)
        # set the connection to 'None' in case of error
        conn = None
    
    # if the connection was successful
    if conn != None:
        cur = conn.cursor()
        
        try:
            cur.execute(songplay_table_create)
            cur.execute(user_table_create)
            cur.execute(song_table_create)
            cur.execute(artist_table_create)
            cur.execute(time_table_create)
            process_data(cur, conn, filepath='data/song_data', func=process_song_file)
            process_data(cur, conn, filepath='data/log_data', func=process_log_file)            
        except Exception as err:
            print ("Oops! An exception has occured in cursor: ", err)
            
        conn.close()
    
if __name__ == "__main__":
    main()