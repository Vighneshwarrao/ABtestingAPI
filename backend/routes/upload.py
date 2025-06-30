from backend.database import SessionLocal,Uploadedfile,Experiment,Variant,Metric,StatisticalTest,TTestDetails,Chi2Details
from backend.abtests import get_variants, t_test,chi2_test
from fastapi import APIRouter,File,UploadFile,Form
import shutil
import os
import pandas as pd

from io import BytesIO
router=APIRouter()
#Creating the Folders to store files

import boto3
from botocore.exceptions import NoCredentialsError

def upload_file_to_s3(file_obj, bucket_name, key):
    s3 = boto3.client("s3")
    try:
        s3.upload_fileobj(file_obj, bucket_name, key, ExtraArgs={"ContentType": "text/csv"})
        return f"https://{bucket_name}.s3.ap-south-1.amazonaws.com/{key}"
    except NoCredentialsError:
        return "Credentials not available"




@router.post("/upload/")
async def uploadfile(file:UploadFile=File(...),variant:str = Form(...),
                     metric:str=Form(...),test_type:str=Form()):
    # ------------Storing the File-----------------------
    from datetime import datetime

    timestamp = datetime.now().strftime("%d%m%Y_%H%M%S")
    base_name = file.filename.rsplit(".", 1)[0]
    ext = file.filename.rsplit(".", 1)[1]

    new_filename = f"{base_name}_{timestamp}.{ext}"
    raw_bytes = await file.read()
    raw_file_buffer = BytesIO(raw_bytes)
    raw_file_buffer.seek(0)
    raw_s3_key = f"raw_files/{new_filename}"
    upload_file_to_s3(raw_file_buffer, "ab-platform-files", raw_s3_key)

    s3 = boto3.client("s3")
    obj = s3.get_object(Bucket="ab-platform-files", Key=raw_s3_key)
    df = pd.read_csv(obj["Body"])
    print(df.columns)
    if  variant not in df.columns:
        return{"message":"Incorrect variant column name."}
    if  metric not in df.columns:
        return{"message":"Incorrect metric column name."}
    df.replace("  ", " -", inplace=True)
    df.dropna(inplace=True)
    if len(df[metric].unique())>2 and test_type=="chi-squared":
        return{"message":"Choose correct test type (Suggestion:T-Test)"}
    if len(df[metric].unique())==2 and test_type=="t-test":
        return {"message": "Choose correct test type (Suggestion:Chi2-Test)"}
    if len(df[variant].unique())!=2:
        return {"message":"This model currently works with files containing only 2 variants."}


    buffer = BytesIO()
    df.to_csv(buffer, index=False)
    buffer.seek(0)
    s3_key = f"cleaned_files/{new_filename}"
    file_url = upload_file_to_s3(buffer, "ab-platform-files", s3_key)
    file_location = s3_key

    # --------Updating experiments table---------------
    session = SessionLocal()
    exp = Experiment(
        exp_name=file.filename,
        exp_status="processing"
    )
    session.add(exp)
    session.flush()

    # --------Updating uploaded_files table---------------
    uploaded = Uploadedfile(
        file_name=file.filename,
        variant=variant,
        metric=metric,
        raw_file_path=raw_s3_key,
        cleaned_file_path=file_location,
        exp_id=exp.exp_id
    )
    session.add(uploaded)
    session.commit()

    # --------Getting the variants---------------
    d = get_variants(variant, file_location)
    variants = [Variant(variant_name=d["var1"],
                        sample_size=d['var1len'],
                        exp_id=exp.exp_id),

                Variant(variant_name=d["var2"],
                        sample_size=d['var2len'],
                        exp_id=exp.exp_id)
                ]
    session.add_all(variants)
    session.commit()
    # -----------------------Testing----------------------------
    if test_type == "t-test":
        l = t_test(variant, metric, file_location, exp.exp_id)
        metrics = [Metric(metric_name=metric,
                          metric_value=l["m1"],
                          exp_id=exp.exp_id,
                          variant_id=variants[0].variant_id),
                   Metric(metric_name=metric,
                          metric_value=l["m2"],
                          exp_id=exp.exp_id,
                          variant_id=variants[1].variant_id)
                   ]
        stats = StatisticalTest(
            test_type=test_type,
            result=l["res"],
            p_value=l["p_val"],
            exp_id=exp.exp_id
        )
        session.add(stats)
        session.flush()
        ttest = TTestDetails(
            exp_id=exp.exp_id,
            test_id=stats.test_id,
            ci_l=l['lower'],
            ci_u=l['upper'],
            t_stat=l['t_stat'],
            var1=l['var1'],
            var2=l['var2'],
            t_critical=l['t_critical'],
            moe=l['moe'],
            dof=l['dof']
        )
        session.add(ttest)
        session.add_all(metrics)
        exp.exp_status = "Completed"
        session.commit()
    else:
        l = chi2_test(variant, metric, file_location, exp.exp_id)
        metrics = [Metric(metric_name=metric,
                          metric_value=l["m1"],
                          exp_id=exp.exp_id,
                          variant_id=variants[0].variant_id),
                   Metric(metric_name=metric,
                          metric_value=l["m2"],
                          exp_id=exp.exp_id,
                          variant_id=variants[1].variant_id)
                   ]
        stats = StatisticalTest(
            test_type=test_type,
            result=l["result"],
            p_value=l["p_val"],
            exp_id=exp.exp_id
        )
        session.add_all(metrics)
        session.add(stats)
        session.flush()
        chi2 = Chi2Details(
            exp_id=exp.exp_id,
            test_id=stats.test_id,
            chi2_stat=l['chi2_stat'],
            dof=l['dof']
        )
        session.add(chi2)
        exp.exp_status = "Completed"
        session.commit()

    return {
        "message": f"{file.filename} uploaded successfully!",
        "file_id": uploaded.file_id,
        "file_name": uploaded.file_name,
        "file_path": uploaded.cleaned_file_path,
        "exp_id":exp.exp_id,
        "test_type":test_type
    }
