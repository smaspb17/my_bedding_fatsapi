from typing import Dict, List, Set

import asyncio
from fastapi_cache.decorator import cache

# Определение ролей и их прав
ROLE_PERMISSIONS: Dict[str, Dict[str, List[str]]] = {
    "admin": {
        "me": ["read", "create", "update", 'delete'],
        "user": ["read", "create", "update", "delete"],
        "shop": ["read", "create", "update", "delete"],
        # "product": ["read", "create", "update", "delete"],
        # "tag": ["read", "create", "update", "delete"],
        # "category": ["read", "create", "update", "delete"],
        # "product_image": ["read", "create", "update", "delete"],
        "cart": ["read", "create", "update", "delete"],
        "order": ["read", "create", "update", "delete"],
        "payment": ["read", "create", "update", "delete"],
    },
    "manager": {
        "me": ["read", "create", "update"],
        "user": ["read", "create", "update"],
        "shop": ["read", "create", "update"],
        # "product": ["read", "create", "update"],
        # "tag": ["read", "create", "update"],
        # "category": ["read", "create", "update"],
        # "product_image": ["read", "create", "update"],
        "cart": ["read"],
        "order": ["read", "create", "update"],
        "payment": ["read"],
    },
    "buyer": {
        "me": ["read", "create", "update"],
        "shop": ["read"],
        # "product": ["read"],
        # "tag": ["read"],
        # "category": ["read"],
        # "product_image": ["read"],
    }, "guest": {
        "shop": ["read"],
    },
}


@cache(expire=60)
async def get_role_scopes(role):
    if role not in ROLE_PERMISSIONS:
        return []
    res = [f"{module}:{action}" for module, actions in ROLE_PERMISSIONS[role].items()
           for action in actions]
    return res


# buyer ['me:read', 'me:create', 'me:update', 'product:read', 'tag:read', 'category:read', 'product_image:read']

