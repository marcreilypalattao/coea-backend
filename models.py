from sqlalchemy import Column, Integer, String, Date, ForeignKey, UniqueConstraint
from database import Base


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    first_name = Column(String(100), nullable=False)
    middle_initial = Column(String(5), default="")
    last_name = Column(String(100), nullable=False)


class YearLevel(Base):
    __tablename__ = "year_levels"
    id = Column(Integer, primary_key=True)
    program = Column(String(150), nullable=False)
    year_level = Column(String(20), nullable=False)
    __table_args__ = (UniqueConstraint("program", "year_level", name="uq_program_year"),)


class Course(Base):
    __tablename__ = "courses"
    id = Column(Integer, primary_key=True)
    code = Column(String(50), nullable=False)
    name = Column(String(200), nullable=False)
    program = Column(String(150), nullable=False)
    year_level = Column(String(20), nullable=False)


class Student(Base):
    __tablename__ = "students"
    id = Column(Integer, primary_key=True)
    course_id = Column(Integer, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    student_id = Column(String(50), nullable=False)   # the school ID number
    last_name = Column(String(100), nullable=False)
    first_name = Column(String(100), nullable=False)
    middle_name = Column(String(100), default="")


class Attendance(Base):
    __tablename__ = "attendance"
    id = Column(Integer, primary_key=True)
    course_id = Column(Integer, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    student_id = Column(String(50), nullable=False)
    date = Column(Date, nullable=False)
    status = Column(String(10), nullable=False)  # Present | Late | Absent | Excuse
    __table_args__ = (UniqueConstraint("course_id", "student_id", "date", name="uq_attendance"),)


class SavedSession(Base):
    __tablename__ = "saved_sessions"
    id = Column(Integer, primary_key=True)
    course_id = Column(Integer, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    date = Column(Date, nullable=False)
    __table_args__ = (UniqueConstraint("course_id", "date", name="uq_session"),)