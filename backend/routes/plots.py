from fastapi import APIRouter
import matplotlib
matplotlib.use('Agg')
from backend.database import SessionLocal,Uploadedfile,Experiment,Variant,Metric,StatisticalTest,TTestDetails,Chi2Details
from matplotlib import pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np
from scipy.stats import chi2,chi2_contingency
import math
import io
import base64
from scipy.stats import t
from statsmodels.graphics.mosaicplot import mosaic
import boto3


def plot_to_base64():
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    img = base64.b64encode(buf.read()).decode('utf-8')
    buf.close()
    plt.close()
    return img

def read_csv_from_s3(key: str, bucket: str = "ab-platform-files") -> pd.DataFrame:
    s3 = boto3.client("s3")
    obj = s3.get_object(Bucket=bucket, Key=key)
    return pd.read_csv(obj["Body"])

router=APIRouter()

@router.get("/get_plots")
def get_plots(exp_id : int):
    session = SessionLocal()
    file = session.query(Uploadedfile).filter(Uploadedfile.exp_id==exp_id).first()
    file_path=file.cleaned_file_path
    df = read_csv_from_s3(file_path)

    test=session.query(StatisticalTest).filter(StatisticalTest.exp_id==exp_id).first()
    if test.test_type=='t-test':
        ttest=session.query(TTestDetails).filter(TTestDetails.exp_id==exp_id).first()
        var1=ttest.var1
        var2=ttest.var2
        t_crit=ttest.t_critical
        t_stat=ttest.t_stat
        moe=ttest.moe
        dof=ttest.dof
        metrics=session.query(Metric).filter(Metric.exp_id==exp_id).all()
        mean1=metrics[0].metric_value
        mean2=metrics[1].metric_value
        size=session.query(Variant).filter(Variant.exp_id==exp_id).all()
        n1=size[0].sample_size
        n2=size[1].sample_size
        means = [mean1, mean2]

        se1 = math.sqrt(var1 / n1)
        se2 = math.sqrt(var2 / n2)

        df1 = n1 - 1
        df2 = n2 - 1

        t1 = t.ppf(0.975, df1)
        t2 = t.ppf(0.975, df2)

        ci1 = t1 * se1
        ci2 = t2 * se2
        ci = [ci1, ci2]
        plt.figure(figsize=(7, 7))
        plt.bar(['VariantA', 'VariantB'], means, yerr=ci, capsize=10)
        plt.ylabel("Metric")
        plt.title("Mean Metric per Variant with 95% Confidence Intervals")
        plt.grid(axis='y')
        bar_plot = plot_to_base64()

        # plot2
        plt.figure(figsize=(7, 7))
        sns.kdeplot(data=df, x=file.metric, hue=file.variant, fill=True, common_norm=False, palette=["#2b8cbe", "#a6bddb"],
                    alpha=0.5)
        plt.title("Distribution of Time Spent")
        plt.xlabel(file.metric)
        plt.ylabel("Density")
        kdeplot = plot_to_base64()

        # plot3
        plt.figure(figsize=(7, 7))
        plt.errorbar([0], [mean2 - mean1], yerr=[moe], fmt='o', capsize=10, color='green',
                     label="Mean difference of A and B")
        plt.axhline(0, color='gray', linestyle='--', label="Zero Difference")
        plt.xticks([0], ["B - A"])
        plt.title("Difference in Means with 95% Confidence Interval")
        plt.ylabel("Difference in Metric")
        plt.legend()
        plt.grid(True)
        diff_mean = plot_to_base64()

        # plot4
        x = np.linspace(-5, 5, 500)
        y = t.pdf(x, dof)
        plt.figure(figsize=(7, 7))
        plt.plot(x, y, label=f't-distribution (df = {dof:.2f})')

        plt.fill_between(x, y, where=(x <= -abs(t_crit)) | (x >= abs(t_crit)), color='red', alpha=0.3,
                         label='Rejection Region (alpha=0.05)')
        plt.axvline(t_stat, color='black', linestyle='--', label=f't-stat = {t_stat:.2f}')
        plt.axvline(-t_stat, color='black', linestyle='--')

        plt.axvline(-t_crit, color='red', linestyle='--', label=f'±t-critical = {t_crit:.2f}')
        plt.axvline(t_crit, color='red', linestyle='--')

        plt.title("Two-Tailed T-Test: P-Value Visualization")
        plt.xlabel("t-value")
        plt.ylabel("Density")
        plt.legend()
        plt.grid(True)
        pplot = plot_to_base64()

        return {'plot1': bar_plot,
                'plot2': kdeplot,
                'plot3': diff_mean,
                'plot4': pplot}
    else:
        variant=file.variant
        metric=file.metric
        chi2_details=session.query(Chi2Details).filter(Chi2Details.exp_id==exp_id).first()
        chi2_stat=chi2_details.chi2_stat
        plt.figure(figsize=(8, 6))
        sns.countplot(data=df, x=variant, hue=metric, palette="Set2")
        plt.title("Observed Counts by Variant and Outcome")
        plt.xlabel("Variant")
        plt.ylabel("Count")
        plt.legend(title=metric)
        plt.grid(axis='y')
        obv_count = plot_to_base64()

        # plot2
        data = df.groupby([variant, metric]).size()
        data_dict = {(str(k1), str(k2)): v for (k1, k2), v in data.items()}
        plt.figure(figsize=(7, 7))
        mosaic(data_dict, title="Mosaic Plot of Variant vs Outcome", labelizer=lambda k: '')
        plt.xlabel("Variant")
        plt.ylabel("Outcome")
        mosiac_plot = plot_to_base64()

        # plot3
        contingency = pd.crosstab(df[variant], df[metric])
        chi2_val, p_val, dof, expected = chi2_contingency(contingency)
        expected_df = pd.DataFrame(expected, index=contingency.index, columns=contingency.columns)

        obs_melted = contingency.reset_index().melt(id_vars=variant, var_name='Metric', value_name='Observed')
        exp_melted = expected_df.reset_index().melt(id_vars=variant, var_name='Metric', value_name='Expected')
        merged = pd.merge(obs_melted, exp_melted, on=[variant, 'Metric'])

        plt.figure(figsize=(7, 7))
        x_labels = merged[variant].astype(str) + ' - ' + merged['Metric'].astype(str)
        x = range(len(x_labels))
        plt.bar(x, merged['Observed'], width=0.4, label='Observed', align='center')
        plt.bar([i + 0.4 for i in x], merged['Expected'], width=0.4, label='Expected', align='center')
        plt.xticks([i + 0.2 for i in x], x_labels, rotation=45)
        plt.ylabel("Count")
        plt.title("Observed vs Expected Counts")
        plt.legend()
        plt.grid(axis='y')
        plt.tight_layout()
        ex_obv = plot_to_base64()

        x = np.linspace(0, chi2.ppf(0.999, dof), 500)
        y = chi2.pdf(x, dof)

        plt.figure(figsize=(8, 6))
        plt.plot(x, y, label='Chi2 Distribution')
        plt.axvline(chi2_stat, color='black', linestyle='--', label=f"Chi2 Stat = {chi2_stat:.2f}")
        plt.fill_between(x, y, where=(x > chi2_stat), color='red', alpha=0.3, label='Rejection Area (p < 0.05)')
        plt.title("Chi-Square Distribution with Test Statistic")
        plt.xlabel("Chi2 Value")
        plt.ylabel("Probability Density")
        plt.legend()
        plt.tight_layout()
        chi2_plot = plot_to_base64()
        return {"plot1": obv_count,
                "plot2": mosiac_plot,
                "plot3": ex_obv,
                "plot4": chi2_plot}

    return {"Error":"Choose valid EXP_ID"}
