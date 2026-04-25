"""Auth helpers: password hashing and validation, login_required decorator."""
from functools import wraps
from typing import Optional, Tuple

from flask import jsonify, session
from werkzeug.security import check_password_hash, generate_password_hash


MIN_PASSWORD_LEN = 8


def hash_password(plain: str) -> str:
    return generate_password_hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    if not plain or not hashed:
        return False
    return check_password_hash(hashed, plain)


def is_valid_password(plain: str) -> Tuple[bool, Optional[str]]:
    if not isinstance(plain, str):
        return False, 'Senha inválida'
    if len(plain) < MIN_PASSWORD_LEN:
        return False, f'Senha precisa ter ao menos {MIN_PASSWORD_LEN} caracteres'
    if plain.strip() == '':
        return False, 'Senha não pode ser vazia'
    return True, None


def is_valid_username(value: str) -> Tuple[bool, Optional[str]]:
    if not isinstance(value, str) or not value.strip():
        return False, 'Usuário é obrigatório'
    if len(value) > 64:
        return False, 'Usuário é muito longo'
    return True, None


def current_user_id() -> Optional[int]:
    return session.get('user_id')


def login_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if current_user_id() is None:
            return jsonify({'error': 'auth required'}), 401
        return view(*args, **kwargs)
    return wrapper
