import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from bson import ObjectId
from typing import List, Optional

from database import db, create_document, get_documents
from schemas import Todo

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Todo API is running"}

@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }

    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"

            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"

    return response

# Helpers
COLLECTION = "todo"

def to_todo(doc: dict) -> dict:
    return {
        "id": str(doc.get("_id")),
        "title": doc.get("title"),
        "completed": bool(doc.get("completed", False)),
        "notes": doc.get("notes"),
        "created_at": doc.get("created_at"),
        "updated_at": doc.get("updated_at"),
    }

# API Models
class TodoCreate(Todo):
    pass

class TodoUpdate(BaseModel):
    title: Optional[str] = None
    completed: Optional[bool] = None
    notes: Optional[str] = None

# Routes
@app.get("/api/todos", response_model=List[dict])
def list_todos():
    docs = get_documents(COLLECTION, {}, limit=None)
    return [to_todo(d) for d in docs]

@app.post("/api/todos", status_code=201)
def create_todo(todo: TodoCreate):
    inserted_id = create_document(COLLECTION, todo)
    doc = db[COLLECTION].find_one({"_id": ObjectId(inserted_id)})
    return to_todo(doc)

@app.patch("/api/todos/{todo_id}")
def update_todo(todo_id: str, payload: TodoUpdate):
    try:
        oid = ObjectId(todo_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid ID")

    updates = {k: v for k, v in payload.model_dump(exclude_unset=True).items()}
    if not updates:
        raise HTTPException(status_code=400, detail="No updates provided")

    updates["updated_at"] = __import__("datetime").datetime.utcnow()
    result = db[COLLECTION].update_one({"_id": oid}, {"$set": updates})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Todo not found")
    doc = db[COLLECTION].find_one({"_id": oid})
    return to_todo(doc)

@app.delete("/api/todos/{todo_id}", status_code=204)
def delete_todo(todo_id: str):
    try:
        oid = ObjectId(todo_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid ID")

    result = db[COLLECTION].delete_one({"_id": oid})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Todo not found")
    return {"status": "deleted"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
