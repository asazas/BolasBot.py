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
                    SeedHash TEXT)''')
    
    cur.execute('''CREATE TABLE IF NOT EXISTS AsyncResults (
                    Id INTEGER PRIMARY KEY AUTOINCREMENT,
                    Race INTEGER REFERENCES AsyncRaces(Id) ON DELETE SET NULL,
                    Player INTEGER REFERENCES Players(DiscordId) ON DELETE SET NULL,
                    Time INTEGER,
                    CollectionRate INTEGER)
                ''')

    mydb.commit()
    mydb.close()


def save_async_result(db_name, member):
    mydb = sqlite3.connect(db_name)
    cur = mydb.cursor()

    cur.execute("SELECT * FROM Players WHERE DiscordId = ?", (member.id, ))
    if not (cur.fetchall()):
        cur.execute("INSERT INTO Players VALUES (?, ?, ?, ?)", (member.id, member.name,
                    member.discriminator, member.mention))
        mydb.commit()
    
    mydb.close()
