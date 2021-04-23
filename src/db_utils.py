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
                    Name TEXT NOT NULL UNIQUE,
                    Creator INTEGER REFERENCES Players(DiscordId) ON DELETE SET NULL,
                    StartDate TEXT NOT NULL,
                    Status INTEGER CHECK (Status == 0 OR Status == 1 OR Status == 2) NOT NULL DEFAULT 0,
                    SeedHash TEXT,
                    SeedUrl TEXT,
                    RoleId INT NOT NULL,
                    ResultsChannel INT NOT NULL,
                    ResultsMessage INT NOT NULL,
                    SpoilersChannel INT NOT NULL)''')
    
    cur.execute('''CREATE TABLE IF NOT EXISTS AsyncResults (
                    Id INTEGER PRIMARY KEY AUTOINCREMENT,
                    Race INTEGER REFERENCES AsyncRaces(Id) ON DELETE SET NULL,
                    Player INTEGER REFERENCES Players(DiscordId) ON DELETE SET NULL,
                    Time INTEGER,
                    CollectionRate INTEGER,
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


def commit_and_close_db(db_conn):
    db_conn.commit()
    db_conn.close()


def insert_player_if_not_exists(db_cur, discord_id, name, discriminator, mention):
    db_cur.execute("SELECT * FROM Players WHERE DiscordId = ?", (discord_id, ))
    if not (db_cur.fetchall()):
        db_cur.execute("INSERT INTO Players VALUES (?, ?, ?, ?)", (discord_id, name,
                    discriminator, mention))


def insert_async(db_cur, name, creator, seed_hash, seed_url, role_id, results_channel, results_message, spoilers_channel):
    db_cur.execute('''INSERT INTO AsyncRaces(Name, Creator, StartDate, Status, SeedHash, SeedUrl, RoleId, ResultsChannel, ResultsMessage, SpoilersChannel) 
                   VALUES (?, ?, datetime('now'), 0, ?, ?, ?, ?, ?, ?)''',
                   (name, creator, seed_hash, seed_url, role_id, results_channel, results_message, spoilers_channel))


def get_async_by_name(db_cur, name):
    db_cur.execute("SELECT * FROM AsyncRaces WHERE Name = ?", (name, ))
    return db_cur.fetchone()


def update_async_status(db_cur, id, status):
    db_cur.execute("UPDATE AsyncRaces SET Status = ? WHERE Id = ?", (status, id))


def save_async_result(db_name, member):
    mydb = sqlite3.connect(db_name)
    cur = mydb.cursor()

    pass
    
    mydb.close()
