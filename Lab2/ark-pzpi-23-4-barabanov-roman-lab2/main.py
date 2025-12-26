import math
from datetime import datetime, timedelta
from typing import List
from contextlib import asynccontextmanager
import json
import io
import uvicorn
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, update, func
from sqlalchemy.orm import selectinload
from passlib.context import CryptContext
from jose import JWTError, jwt
from fastapi.responses import StreamingResponse
from database import engine, Base, get_db
from models import Poll, Option, Vote, Device, User, SystemLog
from schemas import *

SECRET_KEY = "supersecretkey"
ALGORITHM = "HS256"
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


async def log_action(db: AsyncSession, email: str, action: str, details: str = ""):
    db.add(SystemLog(user_email=email, action=action, details=details))
    await db.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(title="Polling System", version="3.3", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"],
                   allow_headers=["*"])


def create_token(data: dict):
    to_encode = data.copy()
    to_encode.update({"exp": datetime.utcnow() + timedelta(minutes=60)})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        if not email: raise HTTPException(401)
    except JWTError:
        raise HTTPException(401)
    res = await db.execute(select(User).where(User.email == email))
    user = res.scalar_one_or_none()
    if not user: raise HTTPException(401)
    return user


async def get_current_admin(user: User = Depends(get_current_user)):
    if user.role != "admin": raise HTTPException(403, "Admins only")
    return user


@app.post("/auth/register", tags=["Auth"])
async def register(user: UserCreate, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(User).where(User.email == user.email))
    if res.scalar_one_or_none(): raise HTTPException(400, "Email exists")

    count = (await db.execute(select(func.count(User.id)))).scalar()
    role = "admin" if count == 0 else "user"

    new_user = User(email=user.email, hashed_password=pwd_context.hash(user.password), role=role)
    db.add(new_user)
    await db.commit()
    await log_action(db, user.email, "REGISTER", f"Role: {role}")
    return new_user


@app.post("/auth/login", response_model=Token, tags=["Auth"])
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(User).where(User.email == form_data.username))
    user = res.scalar_one_or_none()
    if not user or not pwd_context.verify(form_data.password, user.hashed_password):
        raise HTTPException(400, "Bad credentials")

    token = create_token({"sub": user.email, "role": user.role})
    await log_action(db, user.email, "LOGIN")
    return {"access_token": token, "token_type": "bearer", "role": user.role}


@app.get("/admin/users", tags=["Admin"], response_model=List[UserRead])
async def list_users(admin: User = Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    return (await db.execute(select(User))).scalars().all()


@app.patch("/admin/users/{user_id}/role", tags=["Admin"])
async def change_role(user_id: str, data: UserRoleUpdate, admin: User = Depends(get_current_admin),
                      db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(User).where(User.id == user_id))
    user = res.scalar_one_or_none()
    if not user: raise HTTPException(404)
    user.role = data.role
    await db.commit()
    await log_action(db, admin.email, "CHANGE_ROLE", f"User {user.email} -> {data.role}")
    return {"status": "updated"}


@app.get("/admin/backup", tags=["Admin"])
async def create_backup(admin: User = Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    users = (await db.execute(select(User))).scalars().all()
    polls = (await db.execute(select(Poll))).scalars().all()
    votes = (await db.execute(select(Vote))).scalars().all()

    backup_data = {
        "metadata": {"timestamp": str(datetime.utcnow()), "version": "3.0"},
        "users": [{"email": u.email, "role": u.role} for u in users],
        "polls": [{"title": p.title, "room": p.room_id, "active": p.is_active} for p in polls],
        "votes": [{"poll_id": v.poll_id, "device_id": v.device_id, "source": v.source} for v in votes]
    }

    file_stream = io.BytesIO(json.dumps(backup_data, indent=4).encode("utf-8"))

    await log_action(db, admin.email, "BACKUP_CREATED", "Full DB dump downloaded")

    return StreamingResponse(
        file_stream,
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=backup.json"}
    )


@app.get("/admin/logs", tags=["Admin"], response_model=List[SystemLogRead])
async def view_logs(admin: User = Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    return (await db.execute(select(SystemLog).order_by(SystemLog.timestamp.desc()).limit(50))).scalars().all()


@app.post("/polls/", tags=["Polls"], response_model=PollRead)
async def create_poll(poll: PollCreate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    new_poll = Poll(title=poll.title, description=poll.description, room_id=poll.room_id, owner_id=user.id)
    db.add(new_poll)
    await db.flush()
    for opt in poll.options: db.add(Option(poll_id=new_poll.id, text=opt.text))
    await db.commit()
    await log_action(db, user.email, "CREATE_POLL", f"ID: {new_poll.id}")
    query = select(Poll).options(selectinload(Poll.options)).where(Poll.id == new_poll.id)
    result = await db.execute(query)
    final_poll = result.scalar_one()
    return final_poll


@app.get("/polls/my", tags=["Polls"], response_model=List[PollRead])
async def list_my_polls(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    query = (
        select(Poll)
        .options(selectinload(Poll.options))
        .where(Poll.owner_id == user.id)
        .order_by(Poll.created_at.desc())
    )
    res = await db.execute(query)
    polls = res.scalars().all()
    return polls


@app.delete("/polls/{poll_id}", tags=["Polls"])
async def delete_poll(poll_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Poll).where(Poll.id == poll_id))
    poll = res.scalar_one_or_none()
    if not poll: raise HTTPException(404)
    if poll.owner_id != user.id and user.role != "admin": raise HTTPException(403)
    await db.delete(poll)
    await db.commit()
    await log_action(db, user.email, "DELETE_POLL", f"ID: {poll_id}")
    return {"status": "deleted"}


def calculate_stats(options_db):
    total = sum(o.vote_count for o in options_db)
    entropy = 0.0
    if total > 0:
        for o in options_db:
            p = o.vote_count / total
            if p > 0: entropy -= p * math.log2(p)
    stats_opts = []
    for o in options_db:
        p = 0.0 if total == 0 else o.vote_count / total
        err = 1.96 * math.sqrt((p * (1 - p)) / total) if total > 1 else 0.0
        stats_opts.append({"id": o.id, "text": o.text, "vote_count": o.vote_count, "percentage": round(p * 100, 1),
                           "margin_of_error": round(err * 100, 1)})
    return {"analytics": {"total_votes": total, "controversy_index": round(entropy, 2),
                          "consensus_status": "High Controversy" if entropy > 1.0 else "Consensus"},
            "options": stats_opts}


@app.get("/polls/{poll_id}/analytics", response_model=PollReadDetailed, tags=["Public"])
async def get_analytics(poll_id: str, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Poll).where(Poll.id == poll_id))
    poll = res.scalar_one_or_none()
    if not poll: raise HTTPException(404)
    opts = (await db.execute(select(Option).where(Option.poll_id == poll_id))).scalars().all()
    stats = calculate_stats(opts)
    return {**poll.__dict__, "analytics": stats["analytics"], "options": stats["options"]}


@app.post("/iot/register", tags=["IoT"])
async def register_device(dev: DeviceRegister, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Device).where(Device.id == dev.device_id))
    if res.scalar_one_or_none():
        await db.execute(update(Device).where(Device.id == dev.device_id).values(room_id=dev.room_id))
    else:
        db.add(Device(id=dev.device_id, device_type=dev.device_type, room_id=dev.room_id))
    await db.commit()
    return {"status": "registered"}


@app.post("/iot/click", tags=["IoT"])
async def smart_click(click: IoTClick, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Device).where(Device.id == click.device_id))
    device = res.scalar_one_or_none()
    if not device or not device.room_id: raise HTTPException(400, "Device unknown or not assigned")

    p_res = await db.execute(
        select(Poll).where(Poll.room_id == device.room_id, Poll.is_active == True).order_by(Poll.created_at.desc()))
    poll = p_res.scalar_one_or_none()
    if not poll: raise HTTPException(404, "No active poll in room")

    opts = (await db.execute(select(Option).where(Option.poll_id == poll.id))).scalars().all()
    if click.button_index >= len(opts): raise HTTPException(400, "Invalid button")

    selected_opt = opts[click.button_index]
    db.add(Vote(poll_id=poll.id, option_id=selected_opt.id, device_id=device.id, source="iot_room"))
    selected_opt.vote_count += 1
    await db.commit()
    return {"status": "voted", "poll": poll.title, "choice": selected_opt.text}


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)