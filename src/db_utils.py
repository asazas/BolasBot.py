from pathlib import Path

import sqlite3

import discord


def init_db(db_name):
    mydb = sqlite3.connect(db_name)
    cur = mydb.cursor()

    cur.execute('''CREATE TABLE IF NOT EXISTS Players (
                    DiscordId INTEGER NOT NULL PRIMARY KEY,
                    Name TEXT NOT NULL,
                    Discriminator TEXT NOT NULL,
                    Mention TEXT NOT NULL)''')
                    
    cur.execute('''CREATE TABLE IF NOT EXISTS AsyncRaces (
                    Id INTEGER PRIMARY KEY AUTOINCREMENT,
                    Name TEXT NOT NULL,
                    Creator INTEGER REFERENCES Players(DiscordId) ON DELETE SET NULL,
                    StartDate TEXT NOT NULL,
                    Status INTEGER CHECK (Status == 0 OR Status == 1 OR Status == 2) NOT NULL DEFAULT 0,
                    Preset TEXT,
                    SeedHash TEXT,
                    SeedCode TEXT,
                    SeedUrl TEXT,
                    RoleId INT NOT NULL,
                    SubmitChannel INT NOT NULL,
                    ResultsChannel INT NOT NULL,
                    ResultsMessage INT NOT NULL,
                    SpoilersChannel INT NOT NULL)''')
    
    cur.execute('''CREATE TABLE IF NOT EXISTS AsyncResults (
                    Id INTEGER PRIMARY KEY AUTOINCREMENT,
                    Race INTEGER REFERENCES AsyncRaces(Id) ON DELETE SET NULL,
                    Player INTEGER REFERENCES Players(DiscordId) ON DELETE SET NULL,
                    Timestamp TEXT NOT NULL,
                    Time INTEGER NOT NULL DEFAULT '99:59:59',
                    CollectionRate INTEGER NOT NULL DEFAULT 0,
                    UNIQUE(Race, Player))
                ''')

    return (mydb, cur)


def open_db(server):
    my_db = 'data/{}.db'.format(server)
    if not Path(my_db).is_file():
        return init_db(my_db)

    db_conn = sqlite3.connect(my_db)
    db_cur = db_conn.cursor()
    return (db_conn, db_cur)


def commit_db(db_conn):
    db_conn.commit()


def close_db(db_conn):
    db_conn.close()


def get_player_by_id(db_cur, discord_id):
    db_cur.execute("SELECT * FROM Players WHERE DiscordId = ?", (discord_id, ))
    return db_cur.fetchone()


def insert_player_if_not_exists(db_cur, discord_id, name, discriminator, mention):
    if not get_player_by_id(db_cur, discord_id):
        db_cur.execute("INSERT INTO Players VALUES (?, ?, ?, ?)", (discord_id, name,
                    discriminator, mention))


def insert_async(db_cur, name, creator, preset, seed_hash, seed_code, seed_url, role_id, submit_channel, results_channel, results_message, spoilers_channel):
    db_cur.execute('''INSERT INTO AsyncRaces(Name, Creator, StartDate, Status, Preset, SeedHash, SeedCode, SeedUrl, 
                   RoleId, SubmitChannel, ResultsChannel, ResultsMessage, SpoilersChannel) 
                   VALUES (?, ?, datetime('now'), 0, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                   (name, creator, preset, seed_hash, seed_code, seed_url, role_id, submit_channel, results_channel, results_message, spoilers_channel))


def get_active_async_races(db_cur):
    db_cur.execute("SELECT * FROM AsyncRaces WHERE Status = 0 OR Status = 1")
    return db_cur.fetchall()


def search_async_by_name(db_cur, name):
    db_cur.execute("SELECT * FROM AsyncRaces WHERE Name LIKE ?", (name, ))
    return db_cur.fetchall()


def get_async_by_submit(db_cur, subm_channel):
    db_cur.execute("SELECT * FROM AsyncRaces WHERE SubmitChannel = ?", (subm_channel, ))
    return db_cur.fetchone()


def update_async_status(db_cur, id, status):
    db_cur.execute("UPDATE AsyncRaces SET Status = ? WHERE Id = ?", (status, id))


def save_async_result(db_cur, race, player, time, collection_rate):
    db_cur.execute('''REPLACE INTO AsyncResults(Race, Player, Timestamp, Time, CollectionRate)
                   VALUES (?, ?, datetime('now'), ?, ?)''', (race, player, time, collection_rate))


def get_results_for_race(db_cur, submit_channel):
    db_cur.execute('''SELECT Players.Name, AsyncResults.Time, AsyncResults.CollectionRate FROM AsyncResults
                   JOIN AsyncRaces ON AsyncRaces.Id = AsyncResults.Race
                   JOIN Players ON Players.DiscordId = AsyncResults.Player
                   WHERE AsyncRaces.SubmitChannel = ?
                   ORDER BY AsyncResults.Time ASC, datetime(AsyncResults.Timestamp) ASC''', (submit_channel, ))
    return db_cur.fetchall()