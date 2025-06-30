from scipy.stats import ttest_ind,chi2_contingency
from scipy import stats
import pandas as pd
import boto3
from backend.database import SessionLocal,Experiment,Variant,Metric
import numpy  as np
import math

BUCKET_NAME = "ab-platform-files"

# ---- Load CSV from S3 ----
def read_csv_from_s3(key):
    s3 = boto3.client("s3")
    obj = s3.get_object(Bucket=BUCKET_NAME, Key=key)
    return pd.read_csv(obj["Body"])


#--------------Variants--------------------
def get_variants(column:str,file_path:str):
    df=read_csv_from_s3(file_path)
    l=df[column].unique()
    groupa=df[df[column]==l[0]]
    groupb=df[df[column]==l[1]]
    return  {"var1":l[0],"var1len":len(groupa),"var2":l[1],"var2len":len(groupb)}

#--------------------Metrics---------------------
def t_test(variant:str,metric:str,file_path:str,exp_id:int):
    print(exp_id)
    session=SessionLocal()
    variants=session.query(Variant).join(Experiment).filter(Experiment.exp_id==exp_id).all()
    l=[i.variant_name for i in variants]
    df = read_csv_from_s3(file_path)
    groupa=df[df[variant]==l[0]][metric]
    groupb=df[df[variant]==l[1]][metric]
    metric1=groupa.mean()
    metric2=groupb.mean()
    t_stat,p_val=ttest_ind(groupa,groupb)
    print(f"pval:{p_val}")
    result="Reject H0" if p_val<0.05 else "Fail to reject H0"


#----------------confidence interval------------------
    var1=np.var(groupa,ddof=1)
    var2=np.var(groupb,ddof=1)

    n1=len(groupa)
    n2=len(groupb)

    se_diff=math.sqrt((var1/n1)+(var2/n2))

    dof=((var1 / n1 + var2 / n2) ** 2) / (((var1 / n1) ** 2) / (n1 - 1) + ((var2 / n2) ** 2) / (n2 - 1))

    alpha=0.05
    t_critical=stats.t.ppf(1-alpha/2,dof)

    mean_diff=metric1-metric2
    margin_error=t_critical*se_diff

    lower=mean_diff-margin_error
    upper=mean_diff+margin_error


    return {"m1":metric1, "m2":metric2,
            "p_val":p_val,"res":result,
            "lower":lower,"upper":upper,
            "t_stat":t_stat,"t_critical":t_critical,
            "dof":dof,"var1":var1,"var2":var2,"moe":margin_error}


def chi2_test(variant:str,metric:str,file_path:str,exp_id:int):
    session=SessionLocal()
    variants=session.query(Variant).join(Experiment).filter(Experiment.exp_id==exp_id).all()
    l=[i.variant_name for i in variants]

    df = read_csv_from_s3(file_path)
    df[metric]=df[metric].astype(str).str.lower()
    metrics=df[metric].unique()

    positive_val=None
    common_positives = {'1', 'yes', 'clicked', 'true', 'subscribed', 'purchased', 'converted','success'}
    common_negatives = {'0', 'no', 'not_clicked', 'false', 'unsubscribed', 'not_purchased', 'not_converted','fail'}

    for i in metrics:
        if i in common_positives:
            positive_val=i
            break

    if positive_val is None:
        for i in metrics:
            if i not in common_negatives:
                positive_val = i
                break


    groupa=df[df[variant]==l[0]][metric]
    metric1=groupa[groupa==positive_val].shape[0]/len(groupa)
    groupb=df[df[variant]==l[1]][metric]
    metric2=groupb[groupb==positive_val].shape[0]/len(groupb)

    contingency=pd.crosstab(df[variant],df[metric])
    chi2,p_val,dof,expected=chi2_contingency(contingency)
    result="Reject  H0" if p_val<0.05 else "Fail to reject H0"
    return {"m1":metric1,"m2":metric2,
            "p_val":p_val,"result":result,
            "chi2_stat":chi2,"dof":dof}

