from fastapi import APIRouter
from backend.database import SessionLocal,Uploadedfile,Experiment,Variant,Metric,StatisticalTest,TTestDetails,Chi2Details

router=APIRouter()

@router.get("/Summary")
def summarize(exp_id:int):
    session=SessionLocal()
    test=session.query(StatisticalTest).filter(StatisticalTest.exp_id==exp_id).first()
    variants=session.query(Variant).filter(Variant.exp_id==exp_id).all()
    varinat_A=variants[0].variant_name
    varinat_B = variants[1].variant_name
    test_type=test.test_type
    if test_type=='t-test':
        ttest=session.query(TTestDetails).filter(TTestDetails.exp_id==exp_id).first()
        if test.p_value<0.05:
            if ttest.ci_l < 0 and ttest.ci_u <0:
                conclusion=f"Variant {varinat_B} performs significantly differently."
            elif ttest.ci_l > 0 and ttest.ci_u >0:
                conclusion=f"Variant {varinat_A} performs significantly differently."
            else:
                conclusion="No significance difference between the variants."
        else:
            conclusion="No significance difference between the variants."

        summary= (
            f"Test Type: T-Test\n"
            f"Test Statistic: {ttest.t_stat}\n"
            f"Degrees of Freedom: {ttest.dof}\n"
            f"P-value: {test.p_value}\n"
            f"Decision: {test.result}\n"
            f"Conclusion: {conclusion}"
        )
        return{"summary":summary}
    elif test_type=="chi-squared":
        chi2=session.query(Chi2Details).filter(Chi2Details.exp_id==exp_id).first()
        metrics=session.query(Metric).filter(Metric.exp_id==exp_id).all()

        metric_A=metrics[0].metric_value
        metric_B = metrics[1].metric_value
        if test.p_value < 0.05:
            if metric_B > metric_A:
                conclusion=f"Variant {varinat_B} performs significantly differently."
            elif metric_A > metric_B:
                conclusion=f"Variant {varinat_A} performs significantly differently."
            else:
                conclusion="No significance difference between the variants."
        else:
            conclusion="No significance difference between the variants."

        summary=(f"Test Type: {test_type}\n"
            f"Test Statistic: {chi2.chi2_stat}\n"
            f"Degrees of Freedom: {chi2.dof}\n"
            f"P-value: {test.p_value}\n"
            f"Decision: {test.result}\n"
            f"Conclusion: {conclusion}\n"
            f"exp_id : {exp_id}"

        )
        return {"summary":summary}
