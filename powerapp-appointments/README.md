# PowerApp – Appointments Manager

A Microsoft Power Apps canvas application for managing service appointments.
Staff can book, edit, cancel, and view appointments via a mobile-friendly
interface backed by SharePoint Online and Power Automate.

---

## Features

- **Dashboard** – KPI cards for today's appointments and pending count;
  upcoming appointments gallery
- **Create / Edit appointments** – customer + provider dropdowns, date picker,
  time input, duration slider, conflict detection, status management
- **Calendar view** – monthly grid with appointment-day indicators; drill into
  day timeline (08:00–18:00)
- **Search & filter** – full-text search, status chips, and date-range filters
- **Email automation** – instant confirmation email via Power Automate;
  daily 7 AM reminder flow

---

## Documentation

| Document | Description |
|----------|-------------|
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | System design, data flow, component breakdown, security model |
| [`docs/WALKTHROUGH.md`](docs/WALKTHROUGH.md) | Linear step-by-step guide through every screen and action |
| [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) | End-to-end setup: SharePoint, flows, Power Apps Studio, publishing |

---

## Project Structure

```
powerapp-appointments/
├── README.md
├── docs/
│   ├── ARCHITECTURE.md        System design & data flow
│   ├── WALKTHROUGH.md         Linear user walkthrough
│   └── DEPLOYMENT.md          Step-by-step deployment guide
├── src/
│   ├── screens/
│   │   ├── HomeScreen.fx              Dashboard
│   │   ├── AppointmentFormScreen.fx   Create / Edit form
│   │   ├── CalendarScreen.fx          Monthly calendar
│   │   ├── DayViewScreen.fx           Day timeline view
│   │   └── SearchScreen.fx            Search & filter
│   ├── components/
│   │   ├── NavBar.fx                  Bottom navigation bar
│   │   └── StatusBadge.fx             Status pill badge
│   ├── flows/
│   │   ├── SendConfirmationEmail.json  Instant email flow
│   │   └── DailyReminderFlow.json      Scheduled reminder flow
│   ├── connections/
│   │   └── DataConnections.yaml        Connector definitions
│   └── tables/
│       └── AppointmentsSchema.json     SharePoint list schema
└── scripts/
    └── CreateSharePointLists.ps1       PowerShell setup script
```

---

## Quick Start

1. **SharePoint** – run `scripts/CreateSharePointLists.ps1` (or manually
   create lists per `docs/DEPLOYMENT.md` Phase 1).
2. **Power Automate** – import flows from `src/flows/`.
3. **Power Apps** – create a blank canvas app, add connectors, build screens
   using formulas in `src/screens/`, create components from `src/components/`.
4. **Publish & share** – follow `docs/DEPLOYMENT.md` Phase 6.

---

## Technology Stack

- **Frontend**: Microsoft Power Apps (Canvas App, Power Fx)
- **Data**: SharePoint Online lists
- **Automation**: Power Automate Cloud Flows
- **Email**: Office 365 Outlook connector
- **Identity**: Azure Active Directory (Microsoft 365)

---

## Licence

Internal tool – not for redistribution.
