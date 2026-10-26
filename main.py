import hashlib
import hmac
import os
from datetime import date as Date

from fastapi import FastAPI, Depends, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

import models
import schemas
from database import engine, get_db

# Creates the tables in PostgreSQL if they don't exist yet
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="COEA Attendance API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------- Password hashing (standard library only) ----------
def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 200_000)
    return f"{salt.hex()}:{digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    salt_hex, digest_hex = stored.split(":")
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt_hex), 200_000)
    return hmac.compare_digest(digest.hex(), digest_hex)


@app.get("/")
def root():
    return {"message": "COEA Attendance API is running"}


# ================= AUTH =================
@app.post("/auth/register", response_model=schemas.UserOut, status_code=201)
def register(data: schemas.UserCreate, db: Session = Depends(get_db)):
    username = data.username.strip()
    if db.query(models.User).filter(models.User.username == username).first():
        raise HTTPException(400, "Account already exists. Please log in.")
    user = models.User(
        username=username,
        password_hash=hash_password(data.password.strip()),
        first_name=data.first_name.strip(),
        middle_initial=data.middle_initial.strip(),
        last_name=data.last_name.strip(),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@app.post("/auth/login", response_model=schemas.UserOut)
def login(data: schemas.UserLogin, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.username == data.username.strip()).first()
    if not user:
        raise HTTPException(404, "No account existed with this username. Please create an account first.")
    if not verify_password(data.password.strip(), user.password_hash):
        raise HTTPException(401, "Incorrect password.")
    return user


# ================= YEAR LEVELS =================
@app.get("/year-levels", response_model=list[str])
def list_year_levels(program: str, db: Session = Depends(get_db)):
    rows = (
        db.query(models.YearLevel)
        .filter(models.YearLevel.program == program)
        .order_by(models.YearLevel.year_level)
        .all()
    )
    return [r.year_level for r in rows]


@app.post("/year-levels", status_code=201)
def add_year_level(data: schemas.YearLevelCreate, db: Session = Depends(get_db)):
    exists = (
        db.query(models.YearLevel)
        .filter(models.YearLevel.program == data.program, models.YearLevel.year_level == data.year_level)
        .first()
    )
    if not exists:
        db.add(models.YearLevel(program=data.program, year_level=data.year_level))
        db.commit()
    return {"program": data.program, "yearLevel": data.year_level}


@app.delete("/year-levels", status_code=204)
def delete_year_level(program: str, year_level: str, db: Session = Depends(get_db)):
    db.query(models.YearLevel).filter(
        models.YearLevel.program == program, models.YearLevel.year_level == year_level
    ).delete()
    db.commit()
    return Response(status_code=204)


# ================= COURSES =================
@app.get("/courses", response_model=list[schemas.CourseOut])
def list_courses(program: str, year_level: str, db: Session = Depends(get_db)):
    return (
        db.query(models.Course)
        .filter(models.Course.program == program, models.Course.year_level == year_level)
        .order_by(models.Course.code)
        .all()
    )


@app.post("/courses", response_model=schemas.CourseOut, status_code=201)
def add_course(data: schemas.CourseCreate, db: Session = Depends(get_db)):
    course = models.Course(
        code=data.code.strip(), name=data.name.strip(),
        program=data.program, year_level=data.year_level,
    )
    db.add(course)
    db.commit()
    db.refresh(course)
    return course


@app.delete("/courses/{course_id}", status_code=204)
def delete_course(course_id: int, db: Session = Depends(get_db)):
    db.query(models.Attendance).filter(models.Attendance.course_id == course_id).delete()
    db.query(models.SavedSession).filter(models.SavedSession.course_id == course_id).delete()
    db.query(models.Student).filter(models.Student.course_id == course_id).delete()
    db.query(models.Course).filter(models.Course.id == course_id).delete()
    db.commit()
    return Response(status_code=204)


# ================= STUDENTS =================
@app.get("/students", response_model=list[schemas.StudentOut])
def list_students(course_id: int, db: Session = Depends(get_db)):
    return (
        db.query(models.Student)
        .filter(models.Student.course_id == course_id)
        .order_by(models.Student.last_name)
        .all()
    )


@app.post("/students", response_model=schemas.StudentOut, status_code=201)
def add_student(data: schemas.StudentCreate, db: Session = Depends(get_db)):
    if not db.query(models.Course).filter(models.Course.id == data.course_id).first():
        raise HTTPException(404, "Course not found.")
    duplicate = (
        db.query(models.Student)
        .filter(models.Student.course_id == data.course_id, models.Student.student_id == data.student_id.strip())
        .first()
    )
    if duplicate:
        raise HTTPException(409, "This Student ID is already in this course.")
    student = models.Student(
        course_id=data.course_id,
        student_id=data.student_id.strip(),
        last_name=data.last_name.strip(),
        first_name=data.first_name.strip(),
        middle_name=data.middle_name.strip(),
    )
    db.add(student)
    db.commit()
    db.refresh(student)
    return student


@app.delete("/students/{student_pk}", status_code=204)
def delete_student(student_pk: int, db: Session = Depends(get_db)):
    student = db.query(models.Student).filter(models.Student.id == student_pk).first()
    if student:
        db.query(models.Attendance).filter(
            models.Attendance.course_id == student.course_id,
            models.Attendance.student_id == student.student_id,
        ).delete()
        db.delete(student)
        db.commit()
    return Response(status_code=204)


# ================= ATTENDANCE =================
@app.get("/attendance", response_model=list[schemas.AttendanceOut])
def list_attendance(course_id: int, date: Date | None = None, db: Session = Depends(get_db)):
    q = db.query(models.Attendance).filter(models.Attendance.course_id == course_id)
    if date:
        q = q.filter(models.Attendance.date == date)
    return q.all()


@app.put("/attendance", response_model=schemas.AttendanceOut)
def set_attendance(data: schemas.AttendanceSet, db: Session = Depends(get_db)):
    record = (
        db.query(models.Attendance)
        .filter(
            models.Attendance.course_id == data.course_id,
            models.Attendance.student_id == data.student_id,
            models.Attendance.date == data.date,
        )
        .first()
    )
    if record:
        record.status = data.status          # update
    else:
        record = models.Attendance(          # insert
            course_id=data.course_id, student_id=data.student_id,
            date=data.date, status=data.status,
        )
        db.add(record)
    db.commit()
    db.refresh(record)
    return record


# ================= SAVED SESSIONS =================
@app.get("/sessions", response_model=list[Date])
def list_sessions(course_id: int, db: Session = Depends(get_db)):
    rows = (
        db.query(models.SavedSession)
        .filter(models.SavedSession.course_id == course_id)
        .order_by(models.SavedSession.date.desc())
        .all()
    )
    return [r.date for r in rows]


@app.post("/sessions", status_code=201)
def save_session(data: schemas.SessionCreate, db: Session = Depends(get_db)):
    exists = (
        db.query(models.SavedSession)
        .filter(models.SavedSession.course_id == data.course_id, models.SavedSession.date == data.date)
        .first()
    )
    if not exists:
        db.add(models.SavedSession(course_id=data.course_id, date=data.date))
        db.commit()
    return {"courseId": data.course_id, "date": data.date}

@app.delete("/sessions", status_code=204)
def delete_session(course_id: int, date: Date, delete_attendance: bool = False,
                   db: Session = Depends(get_db)):
    db.query(models.SavedSession).filter(
        models.SavedSession.course_id == course_id,
        models.SavedSession.date == date,
    ).delete()
    if delete_attendance:
        db.query(models.Attendance).filter(
            models.Attendance.course_id == course_id,
            models.Attendance.date == date,
        ).delete()
    db.commit()
    return Response(status_code=204)