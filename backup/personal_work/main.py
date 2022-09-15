from email import message
import subprocess 
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import os
import time
import json
import traceback
from bson.json_util import dumps
import csv
from itertools import zip_longest
import pandas as pd
from datetime import datetime
from bson import ObjectId


from celery import Celery
from celery.utils.log import get_task_logger

from dotenv import load_dotenv

# Load env
# -----------------------------------------------------------------------------
ROOT_PATH = os.path.abspath('')
ENV = os.path.join(ROOT_PATH, '.env')
load_dotenv(ENV)

celery = Celery('tasks', broker='amqp://localhost')
celery_log = get_task_logger(__name__)

# Internal Imports
from config import settings

app=FastAPI()

origins = [
    "{}".format(os.environ.get('CORS_ORIGIN_1')),
    "{}".format(os.environ.get('CORS_ORIGIN_2')),
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Item(BaseModel):
    repo_url:str

class Task(BaseModel):
    task_name:str
    branch_name:str
    repo_name:str
    repo_url:str

class TaskResponse(BaseModel):
    task_name:str
    branch_name:str
    repo_name:str
    repo_url:str
    path:str
    status:str
    created_at:str

@app.get("/task-list")
def get_task_list():
    try:
        task_list = list(settings.Tasks.find({}))
        return json.loads(dumps(task_list))

    except Exception as ex:
        # settings.upload_logger.error('Exception occured in task-list - {}'.format(ex))
        return {'message': 'Something went wrong',"error":ex}

@app.post("/create-task")
def create_task(payload:Task):

    try:
        task_obj=payload.dict()
        repo_url = task_obj.get("repo_url")
        task_obj['status'] = "pending"
        now = datetime.utcnow()
        task_obj['created_at'] = now

        _id = settings.Tasks.insert_one(task_obj)
    
        id = json.loads(dumps(_id.inserted_id))
        get_working_directory(repo_url,id['$oid'])
        # get_working_directory(repo_url,id['$oid'])
        return { 
            "message": "Task created successfully",
            "status" : "pending"
            }

    except Exception as error:
        print(traceback.print_exc())
        print("66error",error)
        return {
            "message":"Error occured",
             "error":error
        }

@celery.task
def get_working_directory(repo_url: str,taskId:str):
    if not repo_url:
        return {'message': 'error','data':'please provide the URL'}
    try:
        # Cloning repo into 'cloned' folder.
        os.system("git -C {} clone {}".format(os.environ.get('GIT_CLONE_PATH'),repo_url))
        # get repo name from url.
        repo_name= repo_url.split('.git')[0].split('/')[-1]
        
        # cwd = os.getcwd()
        cwd = os.environ.get('GIT_CLONE_PATH')
        csv=os.environ.get('CSV_PATH')
        os.chdir("{}/{}".format(cwd,repo_name))
        
        os.system("git log --pretty=format:'%H' > {}/log.txt".format(cwd))

        with open('{}/log.txt'.format(cwd), 'r') as commits:
            ids = [line.rstrip() for line in commits]

        res = pd.DataFrame()

        # iterating through the id's
        for id in ids:
            list1=[]
            list2=[]
            name=""
            # Extracting the code difference 
            os.system("git show --unified=0 {}>{}/commit.diff".format(id,cwd))

            # Extracting the required data from commit.diff file
            with open('{}/commit.diff'.format(cwd),'r') as f:
                lines = f.readlines()
                for each in lines:  
                    if each.startswith("diff --git"):
                        name = each.split("/")[-1]
                
                    if "---" not in each and '+++' not in each:
                        if '-' in each[0]:
                            list1.append((name, each.rstrip()))

                        elif '+' in each[0]:
                            list2.append((name, each.rstrip()))

            if len(list1) > len(list2):
                list2.insert(0,(name,None))

            first_df = pd.DataFrame(list1, columns = ['Filename','Buggy/Deleted'])
            second_df = pd.DataFrame(list2, columns = ['Filename','Fixed/Added'])
            final = pd.concat([first_df, second_df[['Fixed/Added']]],1)
            res = pd.concat([res, final])
            # res=res.dropna()

        # create csv file in csvlist folder.
        dir_name = os.path.isdir(csv) 
        
        if dir_name:
            pass
        else:
            os.system('mkdir {}'.format(csv))

        res.to_csv('{}/{}.csv'.format(csv, repo_url.split('/')[-1].replace('.git','')),index=False)
        csv_path = '{}/{}.csv'.format(csv, repo_url.split('/')[-1].replace('.git',''))
        # final.to_csv(csv_path,index=False)
        
        # deleting cloned repo, and other files.n
        clone_dir_name = os.path.isdir("{}/{}".format(os.environ.get('GIT_CLONE_PATH'),repo_name))
        if clone_dir_name:
            os.system("rm -rf {}/{}".format(os.environ.get('GIT_CLONE_PATH'),repo_name))
        
        # deleting commit.diff file
        commit_file_path = os.path.exists("{}/commit.diff".format(os.environ.get('GIT_CLONE_PATH')))
        if commit_file_path: 
            os.system("rm -rf {}/commit.diff".format(os.environ.get('GIT_CLONE_PATH')))

        # deleting log.txt file
        log_file_path = os.path.exists("{}/log.txt".format(os.environ.get('GIT_CLONE_PATH')))
        if log_file_path:
            os.system("rm -rf {}/log.txt".format(os.environ.get('GIT_CLONE_PATH')))

        # updating the status in database
        filter = { '_id': ObjectId(taskId) }
        newvalues = { "$set": { "status" : "success",  "path":csv_path } }
        settings.Tasks.update_one(filter, newvalues)

    except Exception as ex:
        print("Exception in Celery task extract working directory",ex)
        settings.Tasks.update_one(
                {"_id": ObjectId(taskId)},
                {'$set': {"status" : "failed"}})
    



        
            