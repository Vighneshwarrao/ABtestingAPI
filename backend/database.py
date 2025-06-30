from sqlalchemy import create_engine, Integer, String,Float, Column, TIMESTAMP, ForeignKey
from sqlalchemy.orm import declarative_base,sessionmaker,relationship
from sqlalchemy.sql import func


from dotenv import load_dotenv
import os

load_dotenv()

url = os.getenv("DATABASE_URL")

engine=create_engine(url, pool_pre_ping=True)

Base=declarative_base()
class Experiment(Base):
    __tablename__='experiments'

    exp_id = Column(Integer,primary_key=True,autoincrement=True)
    exp_name = Column(String(255))
    created_at=Column(TIMESTAMP,server_default=func.now())
    exp_status=Column(String(255))

    uploaded_files=relationship("Uploadedfile",back_populates="experiment")
    variant =relationship("Variant",back_populates="experiment")
    metric=relationship("Metric",back_populates="experiment")
    statistics=relationship("StatisticalTest",back_populates="experiment")
    ttest=relationship("TTestDetails",back_populates="experiment")
    chi2=relationship("Chi2Details",back_populates="experiment")

class Uploadedfile(Base):
    __tablename__='uploaded_files'

    file_id = Column(Integer, primary_key=True,autoincrement=True)
    file_name = Column(String(255))
    variant=Column(String(255))
    metric=Column(String(255))
    raw_file_path = Column(String(255))
    cleaned_file_path = Column(String(255))
    uploaded_at = Column(TIMESTAMP,server_default=func.now())

    exp_id=Column(Integer,ForeignKey("experiments.exp_id"))
    experiment=relationship("Experiment",back_populates="uploaded_files")


class Variant(Base):
    __tablename__='variants'
    variant_id=Column(Integer,primary_key=True,autoincrement=True)
    variant_name=Column(String(255))
    sample_size=Column(Integer)
    exp_id=Column(Integer,ForeignKey("experiments.exp_id"))


    experiment=relationship("Experiment",back_populates="variant")
    metric=relationship("Metric",back_populates="variant")

class Metric(Base):
    __tablename__='metrics'

    metric_id=Column(Integer,primary_key=True,autoincrement=True)
    metric_name=Column(String(255))
    metric_value=Column(Float)
    calculated_at=Column(TIMESTAMP,server_default=func.now())
    exp_id=Column(Integer,ForeignKey("experiments.exp_id"))
    variant_id=Column(Integer,ForeignKey("variants.variant_id"))

    experiment=relationship("Experiment",back_populates="metric")
    variant=relationship("Variant",back_populates="metric")


class  StatisticalTest(Base):
    __tablename__="statistical_test"

    test_id=Column(Integer,primary_key=True,autoincrement=True)
    test_type=Column(String(255))
    result=Column(String(255))
    p_value=Column(Float)
    executed_at=Column(TIMESTAMP,server_default=func.now())

    exp_id=Column(Integer,ForeignKey("experiments.exp_id"))
    experiment=relationship("Experiment",back_populates="statistics")
    ttest = relationship("TTestDetails", back_populates="statistics")
    chi2=relationship("Chi2Details",back_populates="statistics")
SessionLocal=sessionmaker(bind=engine)

class TTestDetails(Base):
    __tablename__='ttest_details'

    t_test_id=Column(Integer,primary_key=True,autoincrement=True)
    exp_id=Column(Integer,ForeignKey("experiments.exp_id"))
    test_id=Column(Integer,ForeignKey("statistical_test.test_id"))
    ci_l=Column(Float)
    ci_u=Column(Float)
    t_stat=Column(Float)
    var1=Column(Float)
    var2=Column(Float)
    t_critical=Column(Float)
    moe=Column(Float)
    dof=Column(Float)

    experiment = relationship("Experiment", back_populates="ttest")
    statistics=relationship("StatisticalTest",back_populates="ttest")

class Chi2Details(Base):
    __tablename__='chi2_details'

    chi2_id=Column(Integer,primary_key=True,autoincrement=True)
    exp_id=Column(Integer,ForeignKey("experiments.exp_id"))
    test_id=Column(Integer,ForeignKey("statistical_test.test_id"))
    chi2_stat = Column(Float)
    dof = Column(Float)

    experiment = relationship("Experiment", back_populates="chi2")
    statistics=relationship("StatisticalTest",back_populates="chi2")
Base.metadata.create_all(bind=engine)


