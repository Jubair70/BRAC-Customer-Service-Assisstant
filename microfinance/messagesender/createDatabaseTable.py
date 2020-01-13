#!/usr/bin/python

import psycopg2


#def createTable():
conn = psycopg2.connect(database="microfinance", user="microfinanceuser", password="123456", host="127.0.0.1", port="5432")
print "Opened database successfully"
cur = conn.cursor()
cur.execute('''CREATE TABLE message_queue
   (ID INT PRIMARY KEY     NOT NULL,
   subscribeid    TEXT    NOT NULL,
   response       TEXT    NULL,
   status        INT);''')
print "Table created successfully"
conn.commit()
conn.close()