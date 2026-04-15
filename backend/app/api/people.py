from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import uuid

from app.database import get_supabase_admin

router = APIRouter()


class PersonCreate(BaseModel):
    full_name: str
    email: Optional[str] = None
    department: Optional[str] = None
    area: Optional[str] = None
    role: Optional[str] = None


class PersonUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[str] = None
    department: Optional[str] = None
    area: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None


@router.get('')
async def list_people(is_active: Optional[bool] = None, area: Optional[str] = None):
    db = get_supabase_admin()
    query = db.schema('meetingboard').table('people').select('*').order('full_name')
    if is_active is not None:
        query = query.eq('is_active', is_active)
    if area:
        query = query.eq('area', area)
    return query.execute().data


@router.get('/{person_id}')
async def get_person(person_id: str):
    db = get_supabase_admin()
    result = db.schema('meetingboard').table('people').select('*').eq(
        'id', person_id
    ).single().execute()
    if not result.data:
        raise HTTPException(status_code=404, detail='Persona no encontrada')
    return result.data


@router.post('')
async def create_person(body: PersonCreate):
    db = get_supabase_admin()
    result = db.schema('meetingboard').table('people').insert({
        'id': str(uuid.uuid4()),
        **body.model_dump(exclude_none=True),
    }).execute()
    return result.data[0]


@router.patch('/{person_id}')
async def update_person(person_id: str, body: PersonUpdate):
    db = get_supabase_admin()
    data = body.model_dump(exclude_none=True)
    if not data:
        raise HTTPException(status_code=400, detail='No hay datos para actualizar')
    result = db.schema('meetingboard').table('people').update(data).eq(
        'id', person_id
    ).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail='Persona no encontrada')
    return result.data[0]
