# Architecture – PowerApp Appointments Manager

## Overview

The Appointments Manager is a **Microsoft Power Apps canvas app** built on the
Microsoft 365 / Power Platform stack. It targets mobile and tablet form factors
and is designed for front-desk staff who book, edit, and track service
appointments.

---

## High-Level Architecture Diagram

```
┌──────────────────────────────────────────────────────────────────────┐
│                        End Users (Browser / Teams)                   │
│                     Mobile · Desktop · Teams Tab                     │
└─────────────────────────────┬────────────────────────────────────────┘
                              │  HTTPS
                              ▼
┌──────────────────────────────────────────────────────────────────────┐
│                   Power Apps Canvas App                              │
│                                                                      │
│  ┌─────────────┐  ┌──────────────────┐  ┌───────────────┐           │
│  │ HomeScreen  │  │ AppointmentForm  │  │ CalendarScreen│           │
│  │ (dashboard) │  │  Screen (CRUD)   │  │ + DayView     │           │
│  └─────────────┘  └──────────────────┘  └───────────────┘           │
│  ┌─────────────┐  ┌──────────────────┐                               │
│  │SearchScreen │  │ NavBar component │  (reusable components)        │
│  │(filter/sort)│  │ StatusBadge cmp  │                               │
│  └─────────────┘  └──────────────────┘                               │
│                                                                      │
│  Global variables: varCurrentUser, varEditMode,                      │
│                    varSelectedAppointment, varDayViewDate            │
│  Collections:      colTodayAppointments, colUpcoming, colProviders,  │
│                    colCustomers, colMonthAppointments, colDayAppts   │
└────────┬───────────────────────┬──────────────────────┬─────────────┘
         │ SharePoint connector  │ O365 Outlook         │ O365 Users
         ▼                       ▼                      ▼
┌────────────────┐    ┌──────────────────┐   ┌──────────────────┐
│ SharePoint     │    │ Power Automate   │   │ Azure AD /       │
│ Online Lists   │    │ Cloud Flows      │   │ Office 365 Users │
│                │    │                  │   │                  │
│ • Appointments │    │ • Confirmation   │   │ Resolve current  │
│ • Providers    │◄───│   email flow     │   │ user profile     │
│ • Customers    │    │ • Daily reminder │   │ & photo          │
│                │    │   flow (7 AM)    │   │                  │
└────────────────┘    └──────────────────┘   └──────────────────┘
```

---

## Component Breakdown

### Screens

| Screen | Responsibility |
|--------|----------------|
| **HomeScreen** | Dashboard: KPI cards (today / pending counts), upcoming appointments gallery, quick-action buttons |
| **AppointmentFormScreen** | Create and edit appointments. Validates required fields, checks provider conflicts, calls `Patch()` to SharePoint |
| **CalendarScreen** | Monthly grid view. Builds a 42-cell collection (6 weeks). Dots indicate days with appointments. Tap a cell → DayViewScreen |
| **DayViewScreen** | Timeline view 08:00–18:00 in 30-minute slots. Overlays appointment blocks; tap blank slot to pre-fill form |
| **SearchScreen** | Full-text search + status chip filter + date-range pickers. Results sorted descending |

### Components

| Component | Responsibility |
|-----------|----------------|
| **NavBar** | Bottom tab bar (Home / Calendar / Search / + New). Accepts `ActiveScreen` property to highlight the active tab |
| **StatusBadge** | Pill badge rendering status text with semantic colour (green = Confirmed, amber = Pending, red = Cancelled, …) |

### Data Layer

| Entity | SharePoint List | Key columns |
|--------|-----------------|-------------|
| **Appointments** | `Appointments` | CustomerId, ProviderId, AppointmentDate, StartTime, EndTime, Duration, Status, ServiceType, Notes, ReminderSent |
| **Providers** | `Providers` | Title (name), Email, Department, Specialty, IsActive, DefaultDuration, MaxDailyAppointments |
| **Customers** | `Customers` | Title (name), Email, Phone, DateOfBirth, Notes, IsActive |

### Automation (Power Automate Flows)

| Flow | Trigger | What it does |
|------|---------|--------------|
| **SendConfirmationEmail** | PowerApp button (manual) | Sends HTML confirmation email via O365 Outlook; marks `ReminderSent = true` |
| **DailyReminderFlow** | Recurrence – daily 07:00 ET | Queries confirmed appointments for tomorrow where `ReminderSent = false`, emails each customer, marks sent |

---

## Data Flow

### Creating an appointment

```
User fills form
      │
      ▼
btnSave.OnSelect
      │
      ├── locValidationError check (client-side)
      │         └── empty? continue │ non-empty? show error label
      │
      ├── locHasConflict check
      │   (Filter SharePoint for overlapping slots same provider)
      │         └── conflict? show error │ clear? continue
      │
      └── Patch() → SharePoint Appointments list
                │
                └── Navigate(HomeScreen)
                          │
                          └── Screen.OnVisible refreshes colTodayAppointments
                                             & colUpcoming
```

### Sending a confirmation email

```
AppointmentFormScreen (after save)
      │
      └── (Optional) btnConfirm.OnSelect
                │
                └── SendConfirmationEmail flow trigger
                          │
                          ├── O365 Outlook → customer email
                          └── SharePoint PATCH ReminderSent = true
```

---

## State Management

Power Apps uses a flat global variable model. Variables are set at screen level
and scoped as follows:

| Variable | Scope | Purpose |
|----------|-------|---------|
| `varCurrentUser` | Global | Office 365 user profile |
| `varEditMode` | Global | `"New"` or `"Edit"` |
| `varSelectedAppointment` | Global | Record passed to form for editing |
| `varDayViewDate` | Global | Selected date passed to DayViewScreen |
| `varPreFillDate/Time` | Global | Pre-fills form when tapping a day-view slot |
| `locXxx` | Screen-local (`UpdateContext`) | Form field values, loading flags, validation errors |
| `colXxx` | Global collections | Cached data sets loaded on screen navigation |

---

## Security Model

| Concern | Approach |
|---------|---------|
| Authentication | Azure AD (Microsoft 365 login) – enforced by Power Apps platform |
| Authorisation | SharePoint list-level permissions. Staff: Contribute. Managers: Full Control. Customers: none (staff-only app) |
| Data isolation | SharePoint lists inherit site permissions; no row-level security needed for initial version |
| PII | Customer email / phone stored in SharePoint. Tenant data-residency policies apply |
| Flow credentials | Power Automate connections run under the flow owner's identity (or a service account) |

---

## Scalability Limits

| Limit | Value | Mitigation |
|-------|-------|-----------|
| SharePoint delegation | `Filter` on most columns is delegable (Eq, Le, Ge on Date) | Pre-filter by date range; avoid non-delegable operations on large lists |
| Data row limit | Default 500 (configurable to 2000) | Use `SortByColumns` + `Filter` to reduce result sets |
| Concurrent users | Power Apps handles ~100s of concurrent sessions | No backend changes needed for SMB scale |
| Automation throttling | Power Automate Standard: 6,000 runs/day | Sufficient for reminder volumes; upgrade to Premium if needed |

---

## Technology Stack

```
Layer           Technology
──────────────  ──────────────────────────────────
Frontend        Microsoft Power Apps (Canvas App)
Data store      SharePoint Online lists
Automation      Power Automate Cloud Flows
Email           Office 365 Outlook connector
Identity        Azure Active Directory (M365)
Language        Power Fx (formula language)
Deployment      Power Apps environment (maker portal)
```
