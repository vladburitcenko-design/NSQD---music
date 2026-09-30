""" 1 - команда venv\Scripts\activate     2 - команда uvicorn main:app --reload"""

from fastapi import FastAPI, UploadFile, File, Form, Depends, HTTPException
from fastapi.responses import FileResponse
from sqladmin import Admin, ModelView
import models
from database import engine, get_db
from sqlalchemy.orm import Session
import os
models.Base.metadata.create_all(bind=engine)
app = FastAPI(title="Music Streaming API")

MUSIC_DIR = "storage/music"
os.makedirs(MUSIC_DIR, exist_ok=True)


# --- Настройка Админ-панели ---
class UserAdmin(ModelView, model=models.User):
    column_list = [models.User.id, models.User.username, models.User.role]
    icon = "fa-solid fa-user"


class TrackAdmin(ModelView, model=models.Track):
    column_list = [models.Track.id, models.Track.title, models.Track.artist]
    icon = "fa-solid fa-music"


class ReviewAdmin(ModelView, model=models.Review):
    column_list = [models.Review.id, models.Review.track_id, models.Review.rating, models.Review.text]
    icon = "fa-solid fa-comment"


class PlaylistAdmin(ModelView, model=models.Playlist):
    column_list = [models.Playlist.id, models.Playlist.title, models.Playlist.user_id]
    icon = "fa-solid fa-list"


# Подключаем админку
admin = Admin(app, engine, title="Панель управления музыкой")
admin.add_view(UserAdmin)
admin.add_view(TrackAdmin)
admin.add_view(ReviewAdmin)
admin.add_view(PlaylistAdmin)


# --- API Эндпоинты ---

@app.get("/tracks/")
def get_tracks(db: Session = Depends(get_db)):
    """Получить список всех треков"""
    return db.query(models.Track).all()


@app.get("/stream/{track_id}")
def stream_track(track_id: int, db: Session = Depends(get_db)):
    """Отдача аудиофайла в плеер"""
    track = db.query(models.Track).filter(models.Track.id == track_id).first()
    if not track or not os.path.exists(track.file_path):
        raise HTTPException(status_code=404, detail="Трек не найден")
    return FileResponse(track.file_path, media_type="audio/mpeg")


@app.post("/like/")
def toggle_like(user_id: int = Form(...), track_id: int = Form(...), db: Session = Depends(get_db)):
    """Поставить или убрать лайк"""
    existing_like = db.query(models.Like).filter(models.Like.user_id == user_id,
                                                 models.Like.track_id == track_id).first()

    if existing_like:
        db.delete(existing_like)
        db.commit()
        return {"status": "unliked"}
    else:
        new_like = models.Like(user_id=user_id, track_id=track_id)
        db.add(new_like)
        db.commit()
        return {"status": "liked"}


@app.post("/review/")
def add_review(user_id: int = Form(...), track_id: int = Form(...), rating: int = Form(...), text: str = Form(...),
               db: Session = Depends(get_db)):
    """Добавить рецензию к треку"""
    review = models.Review(user_id=user_id, track_id=track_id, rating=rating, text=text)
    db.add(review)
    db.commit()
    return {"status": "review added"}


@app.get("/reviews/{track_id}")
def get_track_reviews(track_id: int, db: Session = Depends(get_db)):
    """Получить все рецензии для конкретного трека"""
    return db.query(models.Review).filter(models.Review.track_id == track_id).all()

@app.get("/all_reviews/")
def get_all_reviews(db: Session = Depends(get_db)):
    """Получить все рецензии для ленты (в стиле Threads)"""
    return db.query(models.Review).order_by(models.Review.id.desc()).all()

@app.get("/liked/{user_id}")
def get_liked_tracks(user_id: int, db: Session = Depends(get_db)):
    """Получить список лайкнутых треков пользователя"""
    liked = db.query(models.Like).filter(models.Like.user_id == user_id).all()
    track_ids = [like.track_id for like in liked]
    return db.query(models.Track).filter(models.Track.id.in_(track_ids)).all()

