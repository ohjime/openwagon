from ninja import NinjaAPI
from core.api import router as core_router
from trip.api import router as trips_router

api = NinjaAPI()

api.add_router("/core", core_router)
api.add_router("/trips", trips_router)
