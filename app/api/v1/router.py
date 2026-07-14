from fastapi import APIRouter

from app.api.v1.endpoints import auth, cart, catalog_refs, favorites, interactions, movies, orders, payments, users

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(movies.router)
api_router.include_router(catalog_refs.router)
api_router.include_router(cart.router)
api_router.include_router(orders.router)
api_router.include_router(payments.router)
api_router.include_router(interactions.router)
api_router.include_router(favorites.router)
