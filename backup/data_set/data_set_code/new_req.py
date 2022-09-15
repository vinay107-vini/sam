import os
import pandas as pd
import re
git_cloned_path="/home/vinay/Desktop/Code/data_set/data_set_code"

# repo_url = input("Enter any public Repo URL: ")
# line_data=int(input("Required lines's "))
# "https://github.com/mapstruct/mapstruct.git","https://github.com/modelmapper/modelmapper.git",
# "https://github.com/orika-mapper/orika.git","https://github.com/remondis-it/remap.git","https://github.com/xebia-france/selma.git"]:

res = pd.DataFrame()
res1 = pd.DataFrame()

for repo_url in ["https://github.com/hrldcpr/pcollections.git","https://github.com/real-logic/simple-binary-encoding.git"]:


    os.system("git -C {} clone {}".format(git_cloned_path,repo_url))

    repo_name= repo_url.split('.git')[0].split('/')[-1]

    cwd = git_cloned_path

    os.chdir("{}/{}".format(cwd,repo_name))

    os.system("git log --pretty=format:'%H' > {}/log.txt".format(cwd))

    with open('{}/log.txt'.format(cwd), 'r') as commits:
        ids = [line.rstrip() for line in commits]

    name="file_name"
        
    for id in ids:
        os.system("git show --unified=0 {}>{}/commit.diff".format(id,cwd))
        with open('{}/commit.diff'.format(cwd),'r',encoding = "ISO-8859-1") as f:
            lines = f.readlines()
            buggy=[]
            fixed=[]
            for data in lines:
                line=data.strip()
                if line.startswith("diff --git"):
                    '''getting the file name'''
                    name = line.split("/")[-1]

                if name.endswith(".java"):       
                    if "---" not in line and '+++' not in line:
                        if line.startswith("-") and re.findall(r"^[a-zA-Z]+\W?[a-zA-Z]*\W?\s*[a-zA-Z]*\s?=\W?[a-zA-Z]*\W?\s?[a-zA-Z]+\W?[a-zA-Z]+\W*[a-zA-Z]*\.[a-zA-Z]*\(\)\)?\;",data[1:].strip()):
                        # if line.startswith("-") and re.findall(r"^[a-zA-Z]+\W?[a-zA-Z]+\W?\s*[a-zA-Z]+\s*=\s*[a-zA-Z]+\.?[a-zA-Z]+\(\)\)?\;",data[1:].strip()):
                            data=line[1:].strip()
                            data_ = data.split()[-1].split('.')[0]
                            final = f"if ({data_} != null ) {data}"
                            fixed.append((name,final))
                            buggy.append((name,data))
                    else:
                        continue
                    
            if buggy and fixed:
                first_df = pd.DataFrame(buggy, columns = ['Filename','Buggy/Deleted'])
                second_df = pd.DataFrame(fixed, columns = ['Filename','Fixed/Added'])
                final = pd.concat([first_df,second_df[['Fixed/Added']]],axis=1)
                res = pd.concat([res, final])
                res1 = pd.concat([res1, final])

    if not res.empty: 
        res1.to_csv('{}/{}.csv'.format(cwd,repo_name),index=False)
        res1 = pd.DataFrame()
  
    # deleting cloned repo, and other files.n
    clone_dir_name = os.path.isdir("{}/{}".format(git_cloned_path,repo_name))
    if clone_dir_name:
        os.system("rm -rf {}/{}".format(git_cloned_path,repo_name))

    # deleting commit.diff file
    commit_file_path = os.path.exists("{}/commit.diff".format(git_cloned_path))
    if commit_file_path: 
        os.system("rm -rf {}/commit.diff".format(git_cloned_path))

    # deleting log.txt file
    log_file_path = os.path.exists("{}/log.txt".format(git_cloned_path))
    if log_file_path:
        os.system("rm -rf {}/log.txt".format(git_cloned_path))

if not res.empty:  
    res.to_csv('{}/data_set4.csv'.format(cwd),index=False)
else:
    raise Exception("No changes in repo")