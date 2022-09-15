import os
import pandas as pd

repo_url = input("Enter any public Repo URL: ")
os.system("git clone {}".format(repo_url))

repo_name= repo_url.split('.git')[0].split('/')[-1]
cwd = os.getcwd()  

os.chdir("{}/{}".format(cwd,repo_name))

os.system("git log --pretty=format:'%H' > {}/log.txt".format(cwd))

with open('{}/log.txt'.format(cwd), 'r') as commits:
    ids = [line.rstrip() for line in commits]
   
'''filter function and skip is used to segregate buggy and fixed code
    and also to create the empty space in pandas dataframe. 

    let say we have a repo which has two commit
    example:- 1st commit data=[
        +java           
        +is easy        
        +language       
    ]
    in 2nd commit data has changed to=[
        -java       +python          
        -is easy    +is very easy    
                    +programming
    ] 
    in above example num_bugs=2 num_fixed=3
    therefore table looks like "buggy"            "fixed"
                                java               python
                                is easy            is very easy
                                -------            programming
   
    our final table should looks like "buggy"      "fixed"
                                       -----        +java           
                                       -----        +is easy        
                                       -----        +language 
                                       -java        +python          
                                       -is easy     +is very easy    

    Next set of buggy and fixed should continue after ------ not in the place of -----
    we have to create the empty sapce in ----- thus it skip rows and continue the proccess
    orelse data with missmatch                             
'''

'''initializing the pandas dataframe'''
res = pd.DataFrame()
name="file_name"

def preprocess(collection):
    global res
    bugs=[]
    fixed=[]
    num_bugs=0
    num_fixed=0
    '''segregate,counting buggy and fixed code where count will be used to create the no of sapce'''

    for data in collection:
        if data[1].startswith("+"):
            fixed.append(data)
            num_fixed+=1
        if data[1].startswith("-"):
            bugs.append(data)
            num_bugs+=1

    space=num_bugs-num_fixed
    if bugs and fixed:
        if space>0:
            for _ in range(abs(space)):
                fixed.append((name,""))
        elif space<0:
            for _ in range(abs(space)):
                bugs.append((name,""))
        fixed.append((name,"---------------------------------------------------"))

    first_df = pd.DataFrame(bugs, columns = ['Filename','Buggy/Deleted'])
    second_df = pd.DataFrame(fixed, columns = ['Filename','Fixed/Added'])
    final = pd.concat([first_df,second_df[['Fixed/Added']]],axis=1)
    res = pd.concat([res, final])

for id in ids:
    '''collection contains bugs and fixed data something like this
    [("file_name","-java"),("file_name","-is easy"),("file_name","+python"),("file_name","+language")]'''
    

    '''commit.diff contains all data regards to commit'''
    os.system("git show --unified=0 {}>{}/commit.diff".format(id,cwd))

    with open('{}/commit.diff'.format(cwd),'r') as f:
        lines = f.readlines()
        bugs_fixed=[]
        for line in lines:
            if line.startswith("diff --git"):
                '''getting the file name'''
                name = line.split("/")[-1]

                '''for example -java        +python
                               -is     
                                easy         easy
                               -language    +programming language

                Usually in dataframe it looks like this -java        +python
                                                        -is          +programming language
                                                        -language 
                which is not correct therefore we have to send the data to the function like this
                1st  (-java,-is,+python) 2nd (-lamguage,+programming language) so that it will be balanced
                '''

            if "---" not in line and '+++' not in line:
                if line.startswith("-") or line.startswith("+") or line.startswith("\ No newline"):
                    bugs_fixed.append((name,line.strip()))
                else:
                    if bugs_fixed:
                        preprocess(bugs_fixed)
                        bugs_fixed=[]
                        
        if bugs_fixed:
            preprocess(bugs_fixed)
    
    if not res.empty:
        '''for each and every commit we are writing the commit_id in dataframe
        to differentiate with other commits'''
        res.loc[len(res.index)] = [f'Commit_ID: {id}', "End of commit", "End of commit"] 

if not res.empty:
    '''if dataframe contains data then we are creating csv file else no'''    
    res.to_csv('{}/data.csv'.format(cwd),index=False)
else:
    raise Exception("No changes in repo")