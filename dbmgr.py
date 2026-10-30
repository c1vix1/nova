import sqlite3

con = sqlite3.connect("tutorial.db")
cur = con.cursor()
cur.execute("CREATE TABLE IF NOT EXIST calender(date,timeStart,timeEnd,info,priority)")
cur.execute("CREATE TABLE IF NOT EXIST assignments(date,timeStart,timeEnd,info,priority)")
cur.execute("CREATE TABLE IF NOT EXIST calender(date,timeStart,timeEnd,info,priority)")