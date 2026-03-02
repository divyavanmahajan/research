# Linear Walkthrough – PowerApp Appointments Manager

This guide walks a new staff member through every screen and action in the app,
from first launch to completing a full appointment lifecycle.

---

## Step 0 – Launch the app

1. Open the Power Apps mobile app **or** navigate to
   `https://make.powerapps.com` → **Apps** → **Appointments Manager** → **Play**.
2. Sign in with your Microsoft 365 account if prompted.
3. The app loads **HomeScreen** and fetches today's appointments and the next
   7 days of upcoming bookings. A loading indicator appears until data is ready.

---

## Step 1 – HomeScreen (Dashboard)

```
┌────────────────────────────────────┐
│  Welcome, Jane Smith               │
│  Monday, March 2 2026              │
│                                    │
│  ┌──────────┐  ┌──────────┐        │
│  │ 4 Today  │  │ 6 Pending│        │
│  └──────────┘  └──────────┘        │
│                                    │
│  [+ New Appointment] [Calendar View]│
│                                    │
│  ── Upcoming ──────────────────    │
│  Mar 3 · 09:00  Alice → Dr. Patel  │
│  Mar 3 · 10:30  Bob   → Dr. Jones  │
│  …                                 │
└────────────────────────────────────┘
```

**What you see:**

| Element | Meaning |
|---------|---------|
| KPI card "4 Today" | Confirmed + pending appointments for today |
| KPI card "6 Pending" | Appointments across the next 7 days awaiting confirmation |
| Upcoming gallery | Next 7 days, sorted by date then time |
| Status colour | Blue = Confirmed, Amber = Pending, Red = Cancelled |

**Actions:**

- Tap **+ New Appointment** → go to Step 2 (create).
- Tap **Calendar View** → go to Step 4 (calendar).
- Tap any row in the gallery → go to Step 3 (edit existing).

---

## Step 2 – Create a New Appointment

After tapping **+ New Appointment**, the **AppointmentFormScreen** opens with
blank defaults.

### 2.1 Select Customer

1. Tap the **Customer** dropdown.
2. A searchable list of active customers appears.
3. Tap the customer's name to select.

> If the customer is not listed, they must first be added via the SharePoint
> Customers list (no in-app customer creation in v1.0).

### 2.2 Select Provider

1. Tap the **Provider** dropdown.
2. Select the provider. The **Duration** slider automatically sets to that
   provider's `DefaultDuration` (e.g. 30 min).

### 2.3 Set Date

1. Tap the **Appointment Date** date picker.
2. Navigate to the desired date and tap **Select**.
3. Dates in the past are rejected at save time.

### 2.4 Set Start Time

1. Tap the **Start Time** text input.
2. Type the time in **HH:MM** format (24-hour), e.g. `14:30`.
3. The **End** label below updates automatically based on Duration.

### 2.5 Adjust Duration

1. Drag the **Duration** slider left (shorter) or right (longer).
2. Steps are 15 minutes; range is 15–240 minutes.
3. The End time label recalculates instantly.

### 2.6 Choose Service Type

1. Tap the **Service Type** dropdown.
2. Choose one of: Consultation / FollowUp / Procedure / Review / Other.

### 2.7 Add Notes (optional)

1. Tap the **Notes** multi-line text box.
2. Type any relevant notes (max 2,000 characters).

### 2.8 Save

1. Tap **Save Appointment**.
2. The app runs validation:
   - Required fields: Customer, Provider, Date, Start Time.
   - Start time format: `HH:MM`.
   - Date must not be in the past (for new bookings).
3. The app checks for **provider conflicts** – if the provider is already
   booked during the selected window, a red error message appears.
4. On success, a `Patch()` call writes the record to SharePoint and the app
   navigates back to HomeScreen. The upcoming gallery refreshes automatically.

---

## Step 3 – Edit an Existing Appointment

1. Tap any appointment row on HomeScreen or SearchScreen.
2. The form pre-populates with existing values.
3. In **Edit mode** the **Status** dropdown is visible (Pending / Confirmed /
   Cancelled / Completed / NoShow).
4. Modify any field and tap **Save Appointment** to update.

### 3.1 Cancel an Appointment

1. Tap **Cancel Appointment** (red outlined button, bottom of form).
2. A confirmation dialog appears: "Cancel this appointment?"
3. Tap **Yes** → Status is set to `Cancelled` in SharePoint. The record
   is no longer shown in upcoming or today's count.

---

## Step 4 – Calendar View

1. Tap **Calendar View** from HomeScreen or the **Calendar** tab in the
   bottom navigation bar.
2. A monthly grid displays with blue dots on days that have appointments.

```
◄  March 2026  ►

Sun  Mon  Tue  Wed  Thu  Fri  Sat
 1    2●   3●   4    5●   6    7
 8    9   10   11   12●  13   14
…
```

### 4.1 Navigate months

- Tap **‹** or **›** to move backward or forward one month.
- The dot indicators reload for the newly displayed month.

### 4.2 Drill into a day

1. Tap any cell → **DayViewScreen** opens for that date.
2. The selected date is highlighted in purple.

---

## Step 5 – Day View (Timeline)

```
Mar 3, 2026 (Tuesday)          ← Calendar

08:00  ─────────────────────────────
08:30  ─────────────────────────────
09:00  ██████████████████████████████  Alice → Dr. Patel [Consultation]
09:30  ██████████████████████████████  (60 min block continues)
10:00  ─────────────────────────────
10:30  ██████████████████████████████  Bob → Dr. Jones [FollowUp]
…

                          [+ New Appointment]
```

- Blue blocks = booked slots. Height is proportional to duration.
- Tapping a **blue block** opens the edit form for that appointment.
- Tapping a **blank slot** opens the new appointment form pre-filled with
  that date and time.

---

## Step 6 – Search & Filter

1. Tap the **Search** tab in the bottom navigation bar.
2. Type in the search box to filter by customer name, provider name, service
   type, or notes content.
3. Tap a **status chip** (All / Pending / Confirmed / Completed / …) to
   narrow by status.
4. Adjust the **From** and **To** date pickers to restrict the date range.
5. The result count label updates live as filters change.
6. Tap any result row to open the edit form.

---

## Step 7 – Sending a Confirmation Email

After saving a new appointment or confirming a pending one:

1. On the edit form, set **Status** to `Confirmed`.
2. Tap **Save Appointment**.
3. *(Optional, if wired to a button)* Tap **Send Confirmation Email** to
   trigger the Power Automate flow that emails the customer immediately.

Alternatively, confirmation emails are sent automatically:

- When staff marks status as **Confirmed** and the **SendConfirmationEmail**
  flow is connected to the `OnSelect` of the Save button.

---

## Step 8 – Automatic Daily Reminders

No manual action needed. The **DailyReminderFlow** runs automatically at
**7:00 AM** every day:

1. Queries all Confirmed appointments scheduled for **tomorrow** where
   `ReminderSent = false`.
2. Sends each customer an HTML reminder email via Office 365.
3. Sets `ReminderSent = true` on each record so reminders are not duplicated.

---

## Appointment Lifecycle Summary

```
Created (Pending)
       │
       ├──► Confirmed ──► Completed  (appointment took place)
       │         │
       │         └──► NoShow        (customer did not attend)
       │
       └──► Cancelled               (cancelled by staff or customer)
```

---

## Navigation Map

```
HomeScreen
  ├── [+ New Appointment]    → AppointmentFormScreen (New)
  ├── [Calendar View]        → CalendarScreen
  ├── [Gallery row tap]      → AppointmentFormScreen (Edit)
  └── [NavBar: Search]       → SearchScreen

CalendarScreen
  ├── [Day cell tap]         → DayViewScreen
  ├── [+ New]                → AppointmentFormScreen (New)
  └── [NavBar: Home]         → HomeScreen

DayViewScreen
  ├── [Blank slot tap]       → AppointmentFormScreen (New, pre-filled)
  ├── [Booked slot tap]      → AppointmentFormScreen (Edit)
  └── [← Calendar]          → CalendarScreen

SearchScreen
  └── [Result row tap]       → AppointmentFormScreen (Edit)

AppointmentFormScreen
  ├── [Save]                 → HomeScreen
  ├── [Cancel Appt]          → HomeScreen (status → Cancelled)
  └── [← Back]              → previous screen
```
