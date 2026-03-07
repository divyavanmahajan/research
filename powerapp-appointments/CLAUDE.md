# PowerApp Appointments — Claude Code Guide

## Project Overview

Microsoft Power Apps canvas application for managing service appointments. No traditional build process — source files are Power Fx formulas and JSON configurations for import into Power Apps Studio.

## Technology

| Layer | Technology |
|---|---|
| Frontend | Power Apps Canvas App (Power Fx) |
| Data | SharePoint Online lists |
| Automation | Power Automate Cloud Flows |
| Email | Office 365 Outlook connector |
| Identity | Azure Active Directory / Microsoft 365 |

## Source Files

```
src/
├── screens/           Power Fx screen formulas (one file per screen)
├── components/        Reusable Power Fx components (NavBar, StatusBadge)
├── flows/             Power Automate flow definitions (JSON)
├── connections/       Data connector definitions (YAML)
└── tables/            SharePoint list schemas (JSON)
scripts/
└── CreateSharePointLists.ps1   PowerShell setup script
```

## Setup Order

1. **SharePoint** — run `scripts/CreateSharePointLists.ps1` to create lists, or follow `docs/DEPLOYMENT.md` Phase 1 manually
2. **Power Automate** — import flows from `src/flows/` (confirmation email + daily reminder)
3. **Power Apps** — create blank canvas app, add connectors per `src/connections/DataConnections.yaml`, build screens using formulas in `src/screens/`
4. **Publish** — follow `docs/DEPLOYMENT.md` Phase 6

## Screens

| File | Screen |
|---|---|
| `HomeScreen.fx` | Dashboard — KPI cards, upcoming appointments |
| `AppointmentFormScreen.fx` | Create / edit appointment form |
| `CalendarScreen.fx` | Monthly calendar grid |
| `DayViewScreen.fx` | Day timeline (08:00–18:00) |
| `SearchScreen.fx` | Full-text search + status/date filters |

## Editing

- `.fx` files contain Power Fx formula source. Paste into the formula bar in Power Apps Studio.
- `.json` flow files are imported via Power Automate > My flows > Import.
- `AppointmentsSchema.json` defines the SharePoint list columns and types.

## Documentation

| Document | Description |
|---|---|
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | System design, data flow, security model |
| [`docs/WALKTHROUGH.md`](docs/WALKTHROUGH.md) | Step-by-step guide through every screen |
| [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) | End-to-end deployment instructions |
