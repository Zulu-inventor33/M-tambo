import pymysql

mydb = pymysql.connect(
        host="localhost",
        user="root",
        passwd = "Nairobi2023#",
        )
my_cursor = mydb.cursor()

#my_cursor.execute("CREATE DATABASE mtambo")

my_cursor.execute("SHOW DATABASES")

for db in my_cursor:
    print(db)
