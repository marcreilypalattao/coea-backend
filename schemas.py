from datetime import date as Date
from typing import Literal
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class CamelModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )


# ---- Auth ----
class UserCreate(CamelModel):
    username: str
    password: str
    first_name: str
    middle_initial: str = ""
    last_name: str


class UserLogin(CamelModel):
    username: str
    password: str


class UserOut(CamelModel):
    id: int
    username: str
    first_name: str
    middle_initial: str
    last_name: str


# ---- Year levels ----
class YearLevelCreate(CamelModel):
    program: str
    year_level: str


# ---- Courses ----
class CourseCreate(CamelModel):
    code: str
    name: str
    program: str
    year_level: str


class CourseOut(CourseCreate):
    id: int


# ---- Students ----
class StudentCreate(CamelModel):
    course_id: int
    student_id: str
    last_name: str
    first_name: str
    middle_name: str = ""


class StudentOut(StudentCreate):
    id: int


# ---- Attendance ----
class AttendanceSet(CamelModel):
    course_id: int
    student_id: str
    date: Date
    status: Literal["Present", "Late", "Absent", "Excuse"]


class AttendanceOut(AttendanceSet):
    pass


# ---- Sessions ----
class SessionCreate(CamelModel):
    course_id: int
    date: Date