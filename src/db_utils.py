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
                    Finished INTEGER CHECK (Finished == 0 OR Finished == 1) NOT NULL DEFAULT 0,
                    SeedHash TEXT,
                    SeedUrl TEXT)''')
    
    cur.execute('''CREATE TABLE IF NOT EXISTS AsyncResults (
                    Id INTEGER PRIMARY KEY AUTOINCREMENT,
                    Race INTEGER REFERENCES AsyncRaces(Id) ON DELETE SET NULL,
                    Player INTEGER REFERENCES Players(DiscordId) ON DELETE SET NULL,
                    Time INTEGER,
                    CollectionRate INTEGER,
                    UNIQUE(Race, Player))
                ''')

    mydb.commit()
    mydb.close()


def get_db_for_server(server):
    my_db = 'data/{}.db'.format(server)
    if not Path(my_db).is_file():
        init_db(my_db)
    return my_db


def insert_player_if_not_exists(db_name, discord_id, name, discriminator, mention):
    mydb = sqlite3.connect(db_name)
    cur = mydb.cursor()

    cur.execute("SELECT * FROM Players WHERE DiscordId = ?", (discord_id, ))
    if not (cur.fetchall()):
        cur.execute("INSERT INTO Players VALUES (?, ?, ?, ?)", (discord_id, name,
                    discriminator, mention))
        mydb.commit()
    
    mydb.close()


def insert_async(db_name, name, creator, seed_hash, seed_url):
    mydb = sqlite3.connect(db_name)
    cur = mydb.cursor()

    cur.execute('''INSERT INTO AsyncRaces(Name, Creator, StartDate, Finished, SeedHash, SeedUrl) 
                VALUES (?, ?, datetime('now'), 0, ?, ?)''', (name, creator, seed_hash, seed_url))
    mydb.commit()

    mydb.close()


def save_async_result(db_name, member):
    mydb = sqlite3.connect(db_name)
    cur = mydb.cursor()

    pass
    
    mydb.close()
