from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import json
import traceback
from bson.json_util import dumps
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
    number_lines:int=None

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
        line_required=task_obj['number_lines']
        now = datetime.utcnow()
        task_obj['created_at'] = now
        _id = settings.Tasks.insert_one(task_obj)
        id = json.loads(dumps(_id.inserted_id))
        get_working_directory.delay(repo_url,id['$oid'],line_required)
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

'''initializing the pandas dataframe'''
res = pd.DataFrame()
name="file_name"
bugs=[]
fixed=[]
num_bugs=0
num_fixed=0

def preprocess(line,line_required):
    global res,bugs,fixed,num_bugs,num_fixed

    if "---" not in line and '+++' not in line:
        if line.startswith("-") or line.startswith("+") or line.startswith("\ No newline"):
            if line.startswith("+"):
                fixed.append((name,line.strip()))
                num_fixed+=1
            if line.startswith("-"):
                bugs.append((name,line.strip()))
                num_bugs+=1
        else:
            space=num_bugs-num_fixed
            if bugs and fixed:
                if space>0:
                    for _ in range(abs(space)):
                        fixed.append((name,""))
                elif space<0:
                    for _ in range(abs(space)):
                        bugs.append((name,""))
                fixed.append((name,"---------------------------------------------------"))
                bugs.append((name,"---------------------------------------------------"))

            if num_bugs==line_required or num_fixed==line_required or line_required==None:
                first_df = pd.DataFrame(bugs, columns = ['Filename','Buggy/Deleted'])
                second_df = pd.DataFrame(fixed, columns = ['Filename','Fixed/Added'])
                final = pd.concat([first_df,second_df[['Fixed/Added']]],axis=1)
                res = pd.concat([res, final])
    else:
        bugs=[]
        fixed=[]
        num_bugs=0
        num_fixed=0
    
@celery.task
def get_working_directory(repo_url: str,taskId:str,line_required):

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

        # iterating through the id's
        for id in ids:
            os.system("git show --unified=0 {}>{}/commit.diff".format(id,cwd))
            with open('{}/commit.diff'.format(cwd),'r') as f:
                lines = f.readlines()
                for line in lines:

                    if line.startswith("diff --git"):
                        '''getting the file name'''
                        global name
                        name = line.split("/")[-1]

                    if line_required==None or line_required>=0:
                        preprocess(line,line_required)

            if not res.empty:
                res.loc[len(res.index)] = [f'Commit_ID: {id}', "End of commit", "End of commit"]

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
        filter_ = { '_id': ObjectId(taskId) }
        newvalues = { "$set": { "status" : "success",  "path":csv_path } }
        settings.Tasks.update_one(filter_, newvalues)

    except Exception as ex:
        print("Exception in Celery task extract working directory",ex)
        settings.Tasks.update_one(
                {"_id": ObjectId(taskId)},
                {'$set': {"status" : "failed"}})
