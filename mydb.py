#we created this file to connecte my sql to the project


import mysql.connector
dataBase = mysql.connector.connect(
    host = 'localhost',
    user = 'root',
    passwd = 'admin',
)

cursorObject = dataBase.cursor()

cursorObject.execute("CREATE DATABASE MYDB")

print("All done") 