"""Shared pytest fixtures for backend tests."""

import pytest
import httpx
from httpx import ASGITransport

from dmv_aptfind.main import app


MOCK_HOME_RESPONSE = {
    "data": {
        "home": {
            "id": "1348599",
            "title": None,
            "rent": 11250,
            "squareMeters": 48,
            "roomCount": 2.0,
            "status": "normal",
            "rentalType": "long_term",
            "shared": False,
            "description": "Charmig och välplanerad 2:a i centrala Göteborg",
            "descriptionBuilding": None,
            "descriptionContract": None,
            "descriptionFeatures": None,
            "descriptionLayout": None,
            "descriptionTransportation": None,
            "floor": None,
            "buildingFloors": None,
            "buildYear": None,
            "bathroomRenovationYear": None,
            "kitchenRenovationYear": None,
            "energyClass": None,
            "tenureType": "condominium",
            "firsthand": False,
            "seniorHome": False,
            "studentHome": False,
            "corporateHome": False,
            "publishedAt": "2026-04-15T10:00:00Z",
            "currency": "SEK",
            "insurance": None,
            "insuranceCost": None,
            "qasaGuarantee": None,
            "qasaGuaranteeCost": None,
            "tenantBaseFee": 519,
            "tenantCount": None,
            "minTenantCount": None,
            "maxTenantCount": None,
            "location": {
                "id": "3382853",
                "latitude": 57.6957305,
                "longitude": 11.9658474,
                "locality": "Göteborg",
                "route": "Föreningsgatan",
                "streetNumber": None,
                "postalCode": "411 27",
                "countryCode": "SE",
                "country": "Sverige",
                "__typename": "Location",
            },
            "uploads": [
                {
                    "id": "19675281",
                    "url": "https://qasa-static-prod.s3-eu-west-1.amazonaws.com/img/test.jpg",
                    "type": "home_picture",
                    "metadata": {
                        "primary": True,
                        "order": 0,
                        "__typename": "UploadMetadata",
                    },
                    "__typename": "Upload",
                }
            ],
            "duration": {
                "id": "12345",
                "startOptimal": None,
                "endOptimal": None,
                "startAsap": True,
                "endUfn": True,
                "possibilityOfExtension": False,
                "__typename": "Duration",
            },
            "traits": [
                {
                    "id": "1",
                    "type": "furniture",
                    "detail": "fully_furnished",
                    "__typename": "Trait",
                },
                {
                    "id": "2",
                    "type": "balcony",
                    "detail": None,
                    "__typename": "Trait",
                },
            ],
            "landlord": {
                "uid": "x7x7cnmg",
                "firstName": "TestUser",
                "companyName": None,
                "professional": False,
                "premium": False,
                "proAgent": False,
                "seenAt": None,
                "createdAt": "2020-01-01T00:00:00Z",
                "__typename": "User",
            },
            "homeTemplates": [
                {
                    "id": "1063155",
                    "apartmentNumber": None,
                    "squareMeters": 48,
                    "roomCount": 2.0,
                    "floor": None,
                    "rent": 11250,
                    "type": "apartment",
                    "description": "Charmig och välplanerad 2:a",
                    "traits": [],
                    "__typename": "HomeTemplate",
                }
            ],
            "__typename": "Home",
        }
    }
}


def make_search_node(node_id: str, rent: int = 10000) -> dict:
    """Create a minimal search result node for testing."""
    return {
        "id": node_id,
        "homeType": "apartment",
        "roomCount": 2.0,
        "bedroomCount": 1,
        "squareMeters": 50,
        "rent": rent,
        "monthlyCost": rent + 519,
        "tenantBaseFee": 519,
        "currency": "SEK",
        "furnished": True,
        "firstHand": False,
        "shared": False,
        "blockListing": False,
        "petsAllowed": True,
        "smokingAllowed": False,
        "wheelchairAccessible": False,
        "instantSign": False,
        "corporateHome": False,
        "seniorHome": False,
        "studentHome": False,
        "shortcutHome": False,
        "finnishLandlordAssociation": False,
        "displayStreetNumber": False,
        "market": "sweden",
        "platform": "dotcom",
        "householdSize": 2,
        "rentalLengthSeconds": 31536000.0,
        "sortingScore": 6.77,
        "description": "Test apartment",
        "title": None,
        "publishedAt": "2026-04-18T17:17:23Z",
        "publishedOrBumpedAt": "2026-04-18T17:17:23Z",
        "lastBumpedAt": None,
        "startDate": "2026-07-01T00:00:00+00:00",
        "endDate": "2027-07-01T00:00:00+00:00",
        "location": {
            "id": 3385831,
            "locality": "Göteborg",
            "countryCode": "SE",
            "route": "Testgatan",
            "streetNumber": None,
            "point": {"lat": 57.7033, "lon": 11.9155, "__typename": "Point"},
            "__typename": "Location",
        },
        "uploads": [
            {
                "id": 19677273,
                "order": 1,
                "type": "home_picture",
                "url": "https://qasa-static-prod.s3-eu-west-1.amazonaws.com/img/test.png",
                "__typename": "Upload",
            }
        ],
        "__typename": "Home",
    }


def make_search_response(
    nodes: list[dict],
    total_count: int,
    pages_count: int,
    has_next_page: bool = False,
) -> dict:
    """Create a mock HomeSearch GraphQL response."""
    return {
        "data": {
            "homeIndexSearch": {
                "documents": {
                    "hasNextPage": has_next_page,
                    "hasPreviousPage": False,
                    "pagesCount": pages_count,
                    "totalCount": total_count,
                    "nodes": nodes,
                    "__typename": "Documents",
                },
                "__typename": "HomeIndexSearch",
            }
        }
    }


@pytest.fixture
def async_client():
    """Create an httpx AsyncClient bound to the FastAPI app for testing."""
    transport = ASGITransport(app=app)
    return httpx.AsyncClient(transport=transport, base_url="http://test")
