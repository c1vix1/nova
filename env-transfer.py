# This file is used to copy your .env to the .env inside the API folder
# Only run when needing to copy
import shutil

source = ".env"
destination = "api/.env" 
shutil.copy2(source, destination)

print("Copy Task Complete")