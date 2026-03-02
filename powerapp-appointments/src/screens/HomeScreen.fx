// =============================================================================
// HomeScreen.fx  –  Dashboard / landing screen
// =============================================================================
// PURPOSE
//   Entry point of the app. Shows today's appointment count, upcoming
//   appointments, and quick-action buttons. Loads reference data once.
// =============================================================================

// ---------------------------------------------------------------------------
// Screen-level OnVisible – runs every time the screen becomes active
// ---------------------------------------------------------------------------
Screen.OnVisible =
    // Refresh appointment data filtered to today + next 7 days
    Concurrent(
        Set(
            varCurrentUser,
            Office365Users.MyProfile()
        ),
        ClearCollect(
            colTodayAppointments,
            Filter(
                SharePointAppointments.Appointments,
                DateValue(Text(AppointmentDate, "yyyy-mm-dd")) = Today()
                    && Status <> "Cancelled"
            )
        ),
        ClearCollect(
            colUpcoming,
            SortByColumns(
                Filter(
                    SharePointAppointments.Appointments,
                    AppointmentDate >= Today()
                        && AppointmentDate <= DateAdd(Today(), 7, TimeUnit.Days)
                        && Status <> "Cancelled"
                        && Status <> "Completed"
                ),
                "AppointmentDate", SortOrder.Ascending,
                "StartTime",       SortOrder.Ascending
            )
        ),
        ClearCollect(
            colProviders,
            Filter(SharePointAppointments.Providers, IsActive = true)
        ),
        ClearCollect(
            colCustomers,
            Filter(SharePointAppointments.Customers, IsActive = true)
        )
    );
    Set(varIsLoading, false)


// ---------------------------------------------------------------------------
// Header Label  –  lblWelcome
// ---------------------------------------------------------------------------
lblWelcome.Text  = "Welcome, " & varCurrentUser.DisplayName
lblWelcome.Font  = Font.'Open Sans'
lblWelcome.Size  = 18
lblWelcome.Color = ColorValue("#1A3C5E")
lblWelcome.X     = 24
lblWelcome.Y     = 16

// ---------------------------------------------------------------------------
// Date Label  –  lblToday
// ---------------------------------------------------------------------------
lblToday.Text  = Text(Today(), "dddd, mmmm d yyyy")
lblToday.Size  = 13
lblToday.Color = ColorValue("#6B7280")
lblToday.X     = 24
lblToday.Y     = 44

// ---------------------------------------------------------------------------
// KPI Card  –  crdTodayCount  (appointments today)
// ---------------------------------------------------------------------------
crdTodayCount.Text         = CountRows(colTodayAppointments) & " Today"
crdTodayCount.Fill         = ColorValue("#EFF6FF")
crdTodayCount.BorderColor  = ColorValue("#3B82F6")
crdTodayCount.BorderThickness = 2
crdTodayCount.Width        = 160
crdTodayCount.Height       = 80
crdTodayCount.X            = 24
crdTodayCount.Y            = 80

// ---------------------------------------------------------------------------
// KPI Card  –  crdPendingCount  (pending confirmation)
// ---------------------------------------------------------------------------
crdPendingCount.Text        = CountRows(Filter(colUpcoming, Status = "Pending")) & " Pending"
crdPendingCount.Fill        = ColorValue("#FFF7ED")
crdPendingCount.BorderColor = ColorValue("#F97316")
crdPendingCount.Width       = 160
crdPendingCount.Height      = 80
crdPendingCount.X           = 200
crdPendingCount.Y           = 80

// ---------------------------------------------------------------------------
// Quick Actions
// ---------------------------------------------------------------------------
btnNewAppointment.Text     = "+ New Appointment"
btnNewAppointment.Fill     = ColorValue("#2563EB")
btnNewAppointment.Color    = Color.White
btnNewAppointment.Width    = 200
btnNewAppointment.Height   = 48
btnNewAppointment.X        = 24
btnNewAppointment.Y        = 180
btnNewAppointment.OnSelect =
    Set(varEditMode, "New");
    Set(varSelectedAppointment, Blank());
    Navigate(AppointmentFormScreen, ScreenTransition.Fade)

btnViewCalendar.Text     = "Calendar View"
btnViewCalendar.Fill     = ColorValue("#10B981")
btnViewCalendar.Color    = Color.White
btnViewCalendar.Width    = 160
btnViewCalendar.Height   = 48
btnViewCalendar.X        = 240
btnViewCalendar.Y        = 180
btnViewCalendar.OnSelect = Navigate(CalendarScreen, ScreenTransition.Fade)

// ---------------------------------------------------------------------------
// Upcoming Appointments Gallery  –  galUpcoming
// ---------------------------------------------------------------------------
galUpcoming.Items      = colUpcoming
galUpcoming.X          = 0
galUpcoming.Y          = 248
galUpcoming.Width      = Parent.Width
galUpcoming.Height     = Parent.Height - 248
galUpcoming.TemplatePadding = 8

// Gallery row template
galUpcoming.Template.Height = 72

// Row: appointment date+time chip
galUpcoming.lblDate.Text  =
    Text(ThisItem.AppointmentDate, "mmm d") & " · " & ThisItem.StartTime
galUpcoming.lblDate.Color = ColorValue("#1D4ED8")
galUpcoming.lblDate.Size  = 12

// Row: customer + provider
galUpcoming.lblSummary.Text =
    ThisItem.CustomerName & "  →  " & ThisItem.ProviderName
galUpcoming.lblSummary.Size = 14
galUpcoming.lblSummary.Color = ColorValue("#111827")

// Row: service type badge
galUpcoming.lblService.Text  = ThisItem.ServiceType
galUpcoming.lblService.Fill  = ColorValue("#F3F4F6")
galUpcoming.lblService.Color = ColorValue("#374151")
galUpcoming.lblService.Size  = 11

// Row: status badge color
galUpcoming.lblStatus.Text = ThisItem.Status
galUpcoming.lblStatus.Color = Switch(
    ThisItem.Status,
    "Confirmed",  ColorValue("#059669"),
    "Pending",    ColorValue("#D97706"),
    "Cancelled",  ColorValue("#DC2626"),
    "Completed",  ColorValue("#6B7280"),
    Color.Black
)

// Row: tap to edit
galUpcoming.OnSelect =
    Set(varSelectedAppointment, ThisItem);
    Set(varEditMode, "Edit");
    Navigate(AppointmentFormScreen, ScreenTransition.Fade)
