import sqlite3

def connection():
    global con 
    con = sqlite3.connect("main.db")
    global cur   
    cur = con.cursor()    

def createTables():
    cur.execute("CREATE TABLE IF NOT EXIST calender(date,timeStart,timeEnd,info,priority)")
    cur.execute("CREATE TABLE IF NOT EXIST assignments(dateDue,timeDue,class,info,priority)")
    cur.execute("CREATE TABLE IF NOT EXIST tasks(date,timeStart,timeEnd,info,priority)")