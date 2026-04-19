# Walkthrough: Apartment Finder Initial Implementation

## Backend Highlights
- **Architecture**: A stateless proxy built with FastAPI. It caches nothing and relies on the Qasa GraphQL API for data.
- **TDD**: 22 tests covering successful fetches, search pagination, and robust error handling for upstream API failures.
- **Client**: Uses `httpx` for async requests with built-in retry logic (simulated in mocks) and server-side pagination to simplify the frontend.

## Frontend Highlights
- **State Management**: Zustand store persists to `localStorage`. Merging logic for JSON imports allows users to sync multiple backups.
- **Map View**: Uses `react-leaflet` with custom SVG markers. Pins are color-coded based on user tags (e.g., green for interested, red for rejected).
- **Split UI**: A modern interface with a glassmorphic side drawer for listing details, keeping the context of the list and map visible.
- **TDD**: 33 tests verifying everything from regex URL parsing to complex store actions and component interactions.

## Key Files
- `backend/services/qasa_client.py`: The heart of the backend API interaction.
- `frontend/src/store/useAppStore.ts`: Central state management with persistence.
- `frontend/src/components/layout/MapPanel.tsx`: Leaflet integration with dynamic pin rendering.
- `frontend/src/components/mylist/ApartmentDetail.tsx`: Side drawer for editing tags and comments.
