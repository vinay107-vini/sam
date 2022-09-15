import os
import pandas as pd

repo_url = input("Enter any public Repo URL: ")
# line_data=int(input("Required lines's "))

os.system("git clone {}".format(repo_url))

repo_name= repo_url.split('.git')[0].split('/')[-1]
cwd = os.getcwd()  

os.chdir("{}/{}".format(cwd,repo_name))

os.system("git log --pretty=format:'%H' > {}/log.txt".format(cwd))

with open('{}/log.txt'.format(cwd), 'r') as commits:
    ids = [line.rstrip() for line in commits]

res = pd.DataFrame()
name="file_name"

def preprocess(collection):
        global res
        bugs=[]
        fixed=[]
        num_bugs=0
        num_fixed=0

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

        # if num_bugs==line_data or num_fixed==line_data or line_data==None:
        if name.endswith(".java"):
            first_df = pd.DataFrame(bugs, columns = ['Filename','Buggy/Deleted'])
            second_df = pd.DataFrame(fixed, columns = ['Filename','Fixed/Added'])
            final = pd.concat([first_df,second_df[['Fixed/Added']]],axis=1)
            res = pd.concat([res, final])

for id in ids:
    os.system("git show --unified=0 {}>{}/commit.diff".format(id,cwd))
    with open('{}/commit.diff'.format(cwd),'r') as f:
        lines = f.readlines()
        bugs_fixed=[]
        for data in lines:
            line=data.strip()
            if line.startswith("diff --git"):
                '''getting the file name'''
                name = line.split("/")[-1]
    
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
        res.loc[len(res.index)] = [f'Commit_ID: {id}', "End of commit", "End of commit"] 

if not res.empty:  
    res.to_csv('{}/data.csv'.format(cwd),index=False)
else:
    raise Exception("No changes in repo")