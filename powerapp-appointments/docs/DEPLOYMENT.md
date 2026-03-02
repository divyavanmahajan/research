# Deployment Guide – PowerApp Appointments Manager

## Prerequisites

| Requirement | Minimum version / plan |
|-------------|------------------------|
| Microsoft 365 licence | Microsoft 365 Business Basic or higher |
| Power Apps licence | Per-app plan **or** Power Apps for Microsoft 365 (included with M365 E3/E5) |
| Power Automate licence | Included with M365; Premium connectors need Power Automate Premium |
| SharePoint Online | Included with M365 |
| Permissions | SharePoint Site Owner **and** Power Platform Environment Admin |

---

## Phase 1 – SharePoint List Setup

### 1.1 Create a SharePoint site

1. Go to `https://<tenant>.sharepoint.com/sites` → **+ Create site**.
2. Choose **Team site**, name it **Appointments**, and note the URL.
3. Add all staff members as **Members** (Contribute permissions).

### 1.2 Create the Appointments list

1. Navigate to the new site → **+ New** → **List** → **Blank list**.
2. Name it exactly `Appointments`.
3. Add columns as specified in `src/tables/AppointmentsSchema.json`:

```
Title            (Single line of text)   – built-in, rename to "Subject"
CustomerId       (Number)
CustomerName     (Single line of text)
ProviderId       (Number)
ProviderName     (Single line of text)
AppointmentDate  (Date and Time)
StartTime        (Single line of text)
EndTime          (Single line of text)
Duration         (Number)
Status           (Choice)               – Pending;Confirmed;Cancelled;Completed;NoShow
ServiceType      (Choice)               – Consultation;FollowUp;Procedure;Review;Other
Notes            (Multiple lines of text)
ReminderSent     (Yes/No, default No)
```

4. Set **Status** default value to `Pending`.
5. Enable **Versioning** (List Settings → Versioning Settings) for audit trail.

### 1.3 Create Providers list

1. **+ New** → **List** → **Blank list** → name `Providers`.
2. Add columns:

```
Title                    (Single line of text)   – built-in, use as "Name"
Email                    (Single line of text)
Department               (Single line of text)
Specialty                (Single line of text)
IsActive                 (Yes/No, default Yes)
MaxDailyAppointments     (Number, default 10)
DefaultDuration          (Number, default 30)
```

3. Populate with at least one provider record before testing the app.

### 1.4 Create Customers list

1. **+ New** → **List** → **Blank list** → name `Customers`.
2. Add columns:

```
Title        (Single line of text)   – built-in, use as "Name"
Email        (Single line of text)
Phone        (Single line of text)
DateOfBirth  (Date and Time)
Notes        (Multiple lines of text)
IsActive     (Yes/No, default Yes)
```

3. Populate with sample records.

---

## Phase 2 – Power Automate Flows

### 2.1 Create SendConfirmationEmail flow

1. Go to `https://make.powerautomate.com` → **+ Create** → **Instant cloud flow**.
2. Name: `SendConfirmationEmail`, trigger: **PowerApps (V2)**.
3. Add inputs matching `src/flows/SendConfirmationEmail.json`:
   `customerEmail`, `customerName`, `providerName`, `appointmentDate`,
   `startTime`, `duration`, `serviceType`, `appointmentId`.
4. Add action: **Office 365 Outlook – Send an email (V2)**.
   - To: `customerEmail` (dynamic content)
   - Subject: `Appointment Confirmed – {appointmentDate} at {startTime}`
   - Body: use the HTML template in the JSON file.
5. Add action: **SharePoint – Update item** on the `Appointments` list:
   - ID: `appointmentId`
   - ReminderSent: `true`
6. **Save** and copy the flow's **Run URL** (shown in the PowerApps trigger step).

### 2.2 Create DailyReminderFlow

1. **+ Create** → **Scheduled cloud flow**.
2. Name: `DailyReminderFlow`, schedule: every **1 Day** at **07:00** in your
   local time zone.
3. Add action: **SharePoint – Get items** from `Appointments` list:
   - Filter query:
     ```
     AppointmentDate eq '<tomorrow>' and Status eq 'Confirmed' and ReminderSent eq false
     ```
     Use the `addDays(utcNow(), 1, 'yyyy-MM-dd')` expression for the date.
4. Add action: **Control – Apply to each** over the returned items.
5. Inside the loop, add **Office 365 Outlook – Send an email (V2)** with the
   reminder template.
6. After the email, add **SharePoint – Update item** to set `ReminderSent = true`.
7. **Save** and **Test** with a manually triggered run.

---

## Phase 3 – Build the Power Apps Canvas App

### 3.1 Open Power Apps Studio

1. Go to `https://make.powerapps.com`.
2. Select the correct **Environment** (top-right dropdown).
3. **+ Create** → **Canvas app from blank** → choose **Phone** or **Tablet**
   layout → name `Appointments Manager`.

### 3.2 Add data connections

1. In the left panel → **Data** → **+ Add data**.
2. Search for and add:
   - **SharePoint** → connect to `https://<tenant>.sharepoint.com/sites/Appointments`
     → select all three lists (Appointments, Providers, Customers).
   - **Office 365 Outlook**
   - **Office 365 Users**

### 3.3 Create screens

Create five screens with these exact names (used by `Navigate()` calls):

| Screen name | Source file |
|-------------|-------------|
| `HomeScreen` | `src/screens/HomeScreen.fx` |
| `AppointmentFormScreen` | `src/screens/AppointmentFormScreen.fx` |
| `CalendarScreen` | `src/screens/CalendarScreen.fx` |
| `DayViewScreen` | `src/screens/DayViewScreen.fx` |
| `SearchScreen` | `src/screens/SearchScreen.fx` |

### 3.4 Add controls from source files

For each screen, add the controls described in the `.fx` source file:

1. Select the screen in the **Tree view**.
2. Insert controls (**+ Insert** menu) matching names used in the formulas.
3. Copy-paste the formula expressions from the `.fx` files into the
   corresponding property fields in the formula bar.

> **Tip:** Use **Ctrl+A** in the formula bar to select all and paste the
> full expression. For `OnVisible` and `OnSelect`, paste the multi-line
> formulas exactly as written.

### 3.5 Create components

1. In the left panel → switch to **Components** tab.
2. **+ New component** for `NavBar` and `StatusBadge`.
3. Add a **Text input property** called `ActiveScreen` to NavBar (default: `"Home"`).
4. Build controls inside each component matching `src/components/NavBar.fx`
   and `src/components/StatusBadge.fx`.
5. Add each component to all primary screens (bottom of screen for NavBar).

### 3.6 Set global variables and App.OnStart

In the **App** object → **OnStart** property:

```powerfx
// Initialise global variables
Set(varEditMode, "New");
Set(varSelectedAppointment, Blank());
Set(varDayViewDate, Today());
Set(varPreFillDate, Today());
Set(varPreFillTime, "09:00");
Set(varIsLoading, true)
```

### 3.7 Configure App settings

1. **File** → **Settings**:
   - **Display**: set to **Phone** or **Tablet** to match your target.
   - **Advanced**: enable **Enhanced delegation** if list exceeds 500 rows.
   - Set **Data row limit** to `2000` (maximum for SharePoint).
2. **File** → **App name** → `Appointments Manager`.

---

## Phase 4 – Connect Power Automate to the App

1. In Power Apps Studio → **Data** → **+ Add data** → search `Power Automate`.
2. Select the `SendConfirmationEmail` flow.
3. In `AppointmentFormScreen`, add a button **Send Confirmation Email** and
   wire its `OnSelect` to:

```powerfx
SendConfirmationEmail.Run(
    locCustomer.Email,
    locCustomer.Title,
    locProvider.Title,
    Text(locDate, "yyyy-mm-dd"),
    locStartTime,
    locDuration,
    locServiceType,
    varSelectedAppointment.ID
)
```

---

## Phase 5 – Testing

### 5.1 Local testing (Studio preview)

1. Press **F5** or the **▶ Play** button in Studio.
2. Walk through the app following the steps in `docs/WALKTHROUGH.md`.
3. Verify:
   - [ ] Appointments list loads on HomeScreen.
   - [ ] New appointment saves correctly to SharePoint.
   - [ ] Conflict detection prevents double-booking.
   - [ ] Calendar dot appears on days with appointments.
   - [ ] DayViewScreen shows correct time blocks.
   - [ ] Search filters work correctly.
   - [ ] Cancel sets status to Cancelled.

### 5.2 End-to-end email test

1. Create a test appointment with your own email as the customer email.
2. Trigger **SendConfirmationEmail** flow manually from Power Automate.
3. Verify email received and `ReminderSent` flag set to `true` in SharePoint.

---

## Phase 6 – Publish & Share

### 6.1 Save and publish

1. **File** → **Save** → **Publish**.
2. Click **Publish this version** in the dialog.

### 6.2 Share with users

1. **File** → **Share**.
2. Enter individual user emails or a Microsoft 365 security group.
3. Grant **Can use** permission (not Can edit, unless they are developers).
4. Ensure users also have **Contribute** access to the SharePoint site.

### 6.3 Add to Microsoft Teams (optional)

1. In Teams → **Apps** → **Build for your org** → **Upload a custom app**.
2. Upload the `.zip` exported from Power Apps (File → Export package → .zip).
3. Pin the app as a Teams tab in the relevant channel.

---

## Phase 7 – Post-deployment Checklist

- [ ] All three SharePoint lists created with correct column names
- [ ] At least one Provider record with `IsActive = true`
- [ ] At least one Customer record with `IsActive = true`
- [ ] SendConfirmationEmail flow saved and tested
- [ ] DailyReminderFlow scheduled and tested
- [ ] App published and shared with staff group
- [ ] Staff trained using WALKTHROUGH.md
- [ ] Data row limit set to 2000 in App Settings
- [ ] SharePoint site permissions reviewed and locked down

---

## Ongoing Maintenance

| Task | Frequency | Who |
|------|-----------|-----|
| Review appointment data for old records | Monthly | Admin |
| Archive completed/cancelled appointments older than 1 year | Quarterly | Admin |
| Check Power Automate flow run history for failures | Weekly | Admin |
| Update Provider or Customer records | As needed | Admin |
| Review and update app if SharePoint list schema changes | On schema change | Developer |

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| Gallery shows no data | SharePoint connection not authorised | Re-add SharePoint connector in Studio; sign in |
| "Delegation warning" yellow triangle | Filter not fully delegable | Increase Data row limit; restructure Filter |
| Conflict check always passes | EndTime column not populated on old records | Run a one-time Flow to compute EndTime from StartTime+Duration |
| Confirmation email not sent | Flow not connected in app or flow disabled | Check Power Automate portal; re-enable and reconnect |
| App opens to blank screen | App.OnStart missing or erroring | Open Studio → check App.OnStart for formula errors |
| Calendar dots missing | colMonthAppointments not refreshing | Verify OnVisible calls ClearCollect correctly; check SharePoint filter |
