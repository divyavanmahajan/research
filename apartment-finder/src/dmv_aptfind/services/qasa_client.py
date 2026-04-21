"""Qasa GraphQL API client.

All external HTTP calls to api.qasa.se are made through this module.
Uses httpx.AsyncClient for non-blocking requests.
"""

import os

import httpx

QASA_GRAPHQL_URL = os.environ.get(
    "QASA_GRAPHQL_URL", "https://api.qasa.se/graphql"
)

HEADERS = {
    "Content-Type": "application/json",
    "Origin": "https://qasa.com",
    "Referer": "https://qasa.com/",
}

HOME_VIEW_QUERY = """
query HomeView($id: ID!) {
  home(id: $id) {
    id
    title
    rent
    squareMeters
    roomCount
    status
    rentalType
    shared
    description
    descriptionBuilding
    descriptionContract
    descriptionFeatures
    descriptionLayout
    descriptionTransportation
    floor
    buildingFloors
    buildYear
    bathroomRenovationYear
    kitchenRenovationYear
    energyClass
    tenureType
    firsthand
    seniorHome
    studentHome
    corporateHome
    publishedAt
    currency
    insurance
    insuranceCost
    qasaGuarantee
    qasaGuaranteeCost
    tenantBaseFee
    tenantCount
    minTenantCount
    maxTenantCount
    location {
      id
      latitude
      longitude
      locality
      route
      streetNumber
      postalCode
      countryCode
      country
      __typename
    }
    uploads {
      id
      url
      type
      metadata {
        primary
        order
        __typename
      }
      __typename
    }
    duration {
      id
      startOptimal
      endOptimal
      startAsap
      endUfn
      possibilityOfExtension
      __typename
    }
    traits {
      id
      type
      detail
      __typename
    }
    landlord {
      uid
      firstName
      companyName
      professional
      premium
      proAgent
      seenAt
      createdAt
      __typename
    }
    homeTemplates {
      id
      apartmentNumber
      squareMeters
      roomCount
      floor
      rent
      type
      description
      traits {
        id
        type
        detail
        __typename
      }
      __typename
    }
    __typename
  }
}
"""

HOME_SEARCH_QUERY = """
query HomeSearch($order: HomeIndexSearchOrderInput, $offset: Int, $limit: Int, $params: HomeSearchParamsInput) {
  homeIndexSearch(order: $order, params: $params) {
    documents(offset: $offset, limit: $limit) {
      hasNextPage
      hasPreviousPage
      nodes {
        bedroomCount
        blockListing
        rentalLengthSeconds
        householdSize
        corporateHome
        description
        endDate
        firstHand
        furnished
        homeType
        id
        instantSign
        market
        lastBumpedAt
        monthlyCost
        petsAllowed
        platform
        publishedAt
        publishedOrBumpedAt
        rent
        currency
        roomCount
        seniorHome
        shared
        shortcutHome
        smokingAllowed
        sortingScore
        squareMeters
        startDate
        studentHome
        tenantBaseFee
        title
        wheelchairAccessible
        finnishLandlordAssociation
        location {
          id
          locality
          countryCode
          streetNumber
          point {
            lat
            lon
            __typename
          }
          route
          __typename
        }
        displayStreetNumber
        uploads {
          id
          order
          type
          url
          __typename
        }
        __typename
      }
      pagesCount
      totalCount
      __typename
    }
    __typename
  }
}
"""

PAGE_SIZE = 59   # Qasa's default page size
MAX_PAGES = 9    # Cap at ~531 results to avoid multi-minute fetches on large cities


async def fetch_listing(home_id: str) -> dict | None:
    """Fetch a single listing from Qasa using the HomeView query.

    Returns the home data dict, or None if the listing doesn't exist.
    Raises httpx.HTTPStatusError on upstream errors.
    """
    async with httpx.AsyncClient() as client:
        response = await client.post(
            QASA_GRAPHQL_URL,
            headers=HEADERS,
            json={
                "operationName": "HomeView",
                "variables": {"id": home_id},
                "query": HOME_VIEW_QUERY,
            },
            timeout=15.0,
        )
        response.raise_for_status()
        data = response.json()
        return data.get("data", {}).get("home")


async def search_listings(
    area_identifier: str,
    *,
    min_room_count: int | None = None,
    max_room_count: int | None = None,
    min_rent: int | None = None,
    max_rent: int | None = None,
    min_square_meters: int | None = None,
    max_square_meters: int | None = None,
    currency: str = "SEK",
    markets: list[str] | None = None,
    furnished: bool | None = None,
    pets_allowed: bool | None = None,
    home_type: str | None = None,
    first_hand: bool | None = None,
    student_home: bool | None = None,
    senior_home: bool | None = None,
    corporate_home: bool | None = None,
    sort_by: str = "published_or_bumped_at",
    sort_direction: str = "descending",
) -> dict:
    """Search Qasa listings, fetching ALL pages server-side.

    Returns a dict with keys: totalCount, pagesCount, results (list of nodes).
    Raises httpx.HTTPStatusError on upstream errors.
    """
    if markets is None:
        markets = ["sweden", "norway", "finland"]

    params: dict = {
        "currency": currency,
        "areaIdentifier": [area_identifier],
        "markets": markets,
    }

    # Add optional filters only if provided
    optional_params = {
        "minRoomCount": min_room_count,
        "maxRoomCount": max_room_count,
        "minRent": min_rent,
        "maxRent": max_rent,
        "minSquareMeters": min_square_meters,
        "maxSquareMeters": max_square_meters,
        "furnished": furnished,
        "petsAllowed": pets_allowed,
        "homeType": home_type,
        "firstHand": first_hand,
        "studentHome": student_home,
        "seniorHome": senior_home,
        "corporateHome": corporate_home,
    }

    for key, value in optional_params.items():
        if value is not None:
            params[key] = value

    order = {"direction": sort_direction, "orderBy": sort_by}

    all_nodes: list[dict] = []
    total_count = 0
    pages_count = 0
    offset = 0
    page = 0

    async with httpx.AsyncClient() as client:
        while page < MAX_PAGES:
            response = await client.post(
                QASA_GRAPHQL_URL,
                headers=HEADERS,
                json={
                    "operationName": "HomeSearch",
                    "variables": {
                        "limit": PAGE_SIZE,
                        "offset": offset,
                        "order": order,
                        "params": params,
                    },
                    "query": HOME_SEARCH_QUERY,
                },
                timeout=15.0,
            )
            response.raise_for_status()
            data = response.json()
            documents = data["data"]["homeIndexSearch"]["documents"]

            all_nodes.extend(documents["nodes"])
            total_count = documents["totalCount"]
            pages_count = documents["pagesCount"]
            page += 1

            if not documents["hasNextPage"]:
                break

            offset += PAGE_SIZE

    return {
        "totalCount": total_count,
        "pagesCount": pages_count,
        "results": all_nodes,
    }
