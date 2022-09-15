# import necessary libraries
import pandas as pd
import os
import glob

# # use glob to get all the csv files
# # in the folder
# path="/home/vinay/Desktop/Code/data_set/data_set_code/data_collection"
# csv_files = glob.glob(os.path.join(path, "*.csv"))

# list=[]
# # loop over the list of csv files
# for f in csv_files:
 
#     # read the csv file
#     df = pd.read_csv(f)
#     list.append(df)

# frame=pd.concat(list,axis=0,ignore_index=True)

# importing pandas package
import pandas as pd

# making data frame from csv file
data = pd.read_csv("null_dataset.csv")

# sorting by first name
data.sort_values("First Name", inplace=True)

# dropping ALL duplicate values
data.drop_duplicates(subset="First Name",
					keep=False, inplace=True)

# displaying data
data
