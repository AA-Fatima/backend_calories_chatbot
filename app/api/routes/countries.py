from fastapi import APIRouter
from typing import List
from app.models.schemas import CountryInfo

router = APIRouter()

COUNTRIES_DATA = [
    CountryInfo(code="lebanon", name_en="Lebanon", name_ar="لبنان", flag_emoji="🇱🇧"),
    CountryInfo(code="syria", name_en="Syria", name_ar="سوريا", flag_emoji="🇸🇾"),
    CountryInfo(code="iraq", name_en="Iraq", name_ar="العراق", flag_emoji="🇮🇶"),
    CountryInfo(code="saudi", name_en="Saudi Arabia", name_ar="السعودية", flag_emoji="🇸🇦"),
    CountryInfo(code="egypt", name_en="Egypt", name_ar="مصر", flag_emoji="🇪🇬"),
    CountryInfo(code="jordan", name_en="Jordan", name_ar="الأردن", flag_emoji="🇯🇴"),
    CountryInfo(code="palestine", name_en="Palestine", name_ar="فلسطين", flag_emoji="🇵🇸"),
    CountryInfo(code="morocco", name_en="Morocco", name_ar="المغرب", flag_emoji="🇲🇦"),
    CountryInfo(code="tunisia", name_en="Tunisia", name_ar="تونس", flag_emoji="🇹🇳"),
    CountryInfo(code="algeria", name_en="Algeria", name_ar="الجزائر", flag_emoji="🇩🇿"),
]

@router.get("/", response_model=List[CountryInfo])
async def get_countries():
    """Get list of supported countries"""
    return COUNTRIES_DATA

@router.get("/{country_code}", response_model=CountryInfo)
async def get_country(country_code: str):
    """Get country by code"""
    for country in COUNTRIES_DATA:
        if country.code == country_code.lower():
            return country
    return {"error": "Country not found"}