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
        before=[]
        after=[]
        num_before=0
        num_after=0
        n=0

        for data in collection:
            if data[1].startswith("public") or "public" in data[1]:
                before.append(data)
                after.append(data)
                n+=1
            else:
                if n>=1 and data[1].startswith("-"):
                    before.append((data[0],data[1][1::]))
                    num_before+=1
                if n>=1 and data[1].startswith("+"):
                    after.append((data[0],data[1][1::]))
                    num_after+=1
                if n>=1 and not data[1].startswith("-") and not data[1].startswith("+"):
                    before.append(data)
                    after.append(data)

        space=num_before-num_after
        if before and after:
            if space>0:
                for _ in range(abs(space)):
                    after.append((name,""))
            elif space<0:
                for _ in range(abs(space)):
                    before.append((name,""))
            after.append((name,"---------------------------------------------------"))
            before.append((name,"---------------------------------------------------"))

        if before and after:           
            first_df = pd.DataFrame(before, columns = ['Filename','Buggy/Deleted'])
            second_df = pd.DataFrame(after, columns = ['Filename','Fixed/Added'])
            final = pd.concat([first_df,second_df[['Fixed/Added']]],axis=1)
            res = pd.concat([res, final])

for id in ids[:-1:]:
    os.system("git show --unified=0 {}>{}/commit.diff".format(id,cwd))
    with open('{}/commit.diff'.format(cwd),'r') as f:
        lines = f.readlines()
        col=[]
        num=0
        for data in lines:
            line=data.strip()
            if line.startswith("diff --git"):
                '''getting the file name'''
                name = line.split("/")[-1]

            if name.endswith(".java"):       
                if line.startswith("@@"):
                    col.append((name,line.strip()))
                    num+=1
                else:
                    if (num>=1 or line.startswith("\ No newline")) and (not line.startswith("diff --git")):
                        col.append((name,line.strip()))
                    else:
                        if col:
                            preprocess(col)
                            num=0
                            # print(col)
                            # print("------------------------------------")
        if col:
            preprocess(col)

   
    if not res.empty:
        res.loc[len(res.index)] = [f'Commit_ID: {id}', "End of commit", "End of commit"] 

if not res.empty:  
    res.to_csv('{}/data.csv'.format(cwd),index=False)
else:
    raise Exception("No changes in repo")