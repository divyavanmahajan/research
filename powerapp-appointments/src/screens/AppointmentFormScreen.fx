// =============================================================================
// AppointmentFormScreen.fx  –  Create / Edit Appointment
// =============================================================================
// PURPOSE
//   Single form used for both new appointments (varEditMode = "New") and
//   editing existing ones (varEditMode = "Edit").
//   Uses varSelectedAppointment to pre-populate fields.
// =============================================================================

// ---------------------------------------------------------------------------
// Screen OnVisible  –  initialise form state
// ---------------------------------------------------------------------------
Screen.OnVisible =
    If(
        varEditMode = "New",
        // Blank defaults for new record
        UpdateContext({
            locCustomer:     Blank(),
            locProvider:     Blank(),
            locDate:         Today(),
            locStartTime:    "09:00",
            locDuration:     30,
            locServiceType:  "Consultation",
            locStatus:       "Pending",
            locNotes:        ""
        }),
        // Pre-fill from selected appointment
        UpdateContext({
            locCustomer:     LookUp(colCustomers,    ID = varSelectedAppointment.CustomerId),
            locProvider:     LookUp(colProviders,    ID = varSelectedAppointment.ProviderId),
            locDate:         DateValue(Text(varSelectedAppointment.AppointmentDate, "yyyy-mm-dd")),
            locStartTime:    varSelectedAppointment.StartTime,
            locDuration:     varSelectedAppointment.Duration,
            locServiceType:  varSelectedAppointment.ServiceType,
            locStatus:       varSelectedAppointment.Status,
            locNotes:        varSelectedAppointment.Notes
        })
    );
    UpdateContext({ locFormError: "", locSaving: false })

// ---------------------------------------------------------------------------
// Header
// ---------------------------------------------------------------------------
lblFormTitle.Text  = If(varEditMode = "New", "New Appointment", "Edit Appointment")
lblFormTitle.Size  = 20
lblFormTitle.Color = ColorValue("#1A3C5E")
lblFormTitle.X     = 24
lblFormTitle.Y     = 16

btnBack.Text     = "← Back"
btnBack.OnSelect = Navigate(HomeScreen, ScreenTransition.Back)
btnBack.X        = Parent.Width - 120
btnBack.Y        = 16

// ---------------------------------------------------------------------------
// Customer Dropdown  –  ddCustomer
// ---------------------------------------------------------------------------
lblCustomer.Text = "Customer *"
lblCustomer.Y    = 72

ddCustomer.Items       = colCustomers
ddCustomer.Value       = "Title"
ddCustomer.Default     = locCustomer
ddCustomer.Y           = 92
ddCustomer.Width       = Parent.Width - 48
ddCustomer.X           = 24
ddCustomer.OnChange    = UpdateContext({ locCustomer: ddCustomer.Selected })

// ---------------------------------------------------------------------------
// Provider Dropdown  –  ddProvider
// ---------------------------------------------------------------------------
lblProvider.Text = "Provider *"
lblProvider.Y    = 148

ddProvider.Items    = colProviders
ddProvider.Value    = "Title"
ddProvider.Default  = locProvider
ddProvider.Y        = 168
ddProvider.Width    = Parent.Width - 48
ddProvider.X        = 24
ddProvider.OnChange =
    UpdateContext({
        locProvider: ddProvider.Selected,
        locDuration: ddProvider.Selected.DefaultDuration
    })

// ---------------------------------------------------------------------------
// Date Picker  –  dtpDate
// ---------------------------------------------------------------------------
lblDate.Text = "Appointment Date *"
lblDate.Y    = 224

dtpDate.DefaultDate = locDate
dtpDate.Y           = 244
dtpDate.X           = 24
dtpDate.Width       = (Parent.Width / 2) - 32
dtpDate.OnChange    = UpdateContext({ locDate: dtpDate.SelectedDate })

// ---------------------------------------------------------------------------
// Start Time  –  txtStartTime
// ---------------------------------------------------------------------------
lblStartTime.Text = "Start Time (HH:MM) *"
lblStartTime.Y    = 224
lblStartTime.X    = Parent.Width / 2

txtStartTime.Default = locStartTime
txtStartTime.Y       = 244
txtStartTime.X       = Parent.Width / 2
txtStartTime.Width   = (Parent.Width / 2) - 24
txtStartTime.HintText = "09:00"
txtStartTime.OnChange = UpdateContext({ locStartTime: txtStartTime.Text })

// ---------------------------------------------------------------------------
// Duration Slider  –  sldDuration
// ---------------------------------------------------------------------------
lblDuration.Text = "Duration: " & locDuration & " minutes"
lblDuration.Y    = 308

sldDuration.Min     = 15
sldDuration.Max     = 240
sldDuration.Step    = 15
sldDuration.Default = locDuration
sldDuration.Y       = 328
sldDuration.X       = 24
sldDuration.Width   = Parent.Width - 48
sldDuration.OnChange = UpdateContext({ locDuration: sldDuration.Value })

// Computed end time label
lblEndTime.Text =
    "End: " & Text(
        TimeValue(locStartTime) + Time(0, locDuration, 0),
        "HH:MM"
    )
lblEndTime.Y    = 352
lblEndTime.Color = ColorValue("#6B7280")

// ---------------------------------------------------------------------------
// Service Type  –  ddServiceType
// ---------------------------------------------------------------------------
lblServiceType.Text = "Service Type *"
lblServiceType.Y    = 376

ddServiceType.Items   = ["Consultation","FollowUp","Procedure","Review","Other"]
ddServiceType.Default = locServiceType
ddServiceType.Y       = 396
ddServiceType.X       = 24
ddServiceType.Width   = (Parent.Width / 2) - 32
ddServiceType.OnChange = UpdateContext({ locServiceType: ddServiceType.Selected.Value })

// ---------------------------------------------------------------------------
// Status  –  ddStatus  (Edit mode only)
// ---------------------------------------------------------------------------
lblStatus.Text    = "Status"
lblStatus.Y       = 376
lblStatus.X       = Parent.Width / 2
lblStatus.Visible = varEditMode = "Edit"

ddStatus.Items    = ["Pending","Confirmed","Cancelled","Completed","NoShow"]
ddStatus.Default  = locStatus
ddStatus.Y        = 396
ddStatus.X        = Parent.Width / 2
ddStatus.Width    = (Parent.Width / 2) - 24
ddStatus.Visible  = varEditMode = "Edit"
ddStatus.OnChange = UpdateContext({ locStatus: ddStatus.Selected.Value })

// ---------------------------------------------------------------------------
// Notes  –  txtNotes
// ---------------------------------------------------------------------------
lblNotes.Text = "Notes"
lblNotes.Y    = 460

txtNotes.Default   = locNotes
txtNotes.Y         = 480
txtNotes.X         = 24
txtNotes.Width     = Parent.Width - 48
txtNotes.Height    = 100
txtNotes.Mode      = TextMode.MultiLine
txtNotes.OnChange  = UpdateContext({ locNotes: txtNotes.Text })

// ---------------------------------------------------------------------------
// Validation helper
// ---------------------------------------------------------------------------
// Returns "" if valid, or an error message string
locValidationError =
    If(
        IsBlank(locCustomer),
        "Please select a customer.",
        IsBlank(locProvider),
        "Please select a provider.",
        IsBlank(locDate),
        "Please select a date.",
        Not(IsMatch(locStartTime, "^([01]?[0-9]|2[0-3]):[0-5][0-9]$")),
        "Start time must be in HH:MM format (e.g. 09:00).",
        locDate < Today() && varEditMode = "New",
        "Appointment date cannot be in the past.",
        ""
    )

// ---------------------------------------------------------------------------
// Conflict check function (inline)
// ---------------------------------------------------------------------------
// Returns true if slot already booked for that provider
locHasConflict =
    !IsEmpty(
        Filter(
            SharePointAppointments.Appointments,
            ProviderId = locProvider.ID
                && DateValue(Text(AppointmentDate, "yyyy-mm-dd")) = locDate
                && Status <> "Cancelled"
                && ID     <> If(varEditMode = "Edit", varSelectedAppointment.ID, 0)
                && TimeValue(StartTime) < TimeValue(locStartTime) + Time(0, locDuration, 0)
                && TimeValue(EndTime)   > TimeValue(locStartTime)
        )
    )

// ---------------------------------------------------------------------------
// Error label
// ---------------------------------------------------------------------------
lblError.Text    = locFormError
lblError.Color   = ColorValue("#DC2626")
lblError.Visible = locFormError <> ""
lblError.Y       = 596
lblError.X       = 24

// ---------------------------------------------------------------------------
// Save Button  –  btnSave
// ---------------------------------------------------------------------------
btnSave.Text    = If(locSaving, "Saving…", "Save Appointment")
btnSave.Fill    = ColorValue("#2563EB")
btnSave.Color   = Color.White
btnSave.Width   = Parent.Width - 48
btnSave.Height  = 52
btnSave.X       = 24
btnSave.Y       = 624
btnSave.Disabled = locSaving

btnSave.OnSelect =
    // 1. Validate
    If(
        locValidationError <> "",
        UpdateContext({ locFormError: locValidationError }),

        // 2. Conflict check
        locHasConflict,
        UpdateContext({ locFormError: "That time slot is already booked for this provider. Please choose a different time." }),

        // 3. Save
        UpdateContext({ locSaving: true, locFormError: "" });
        If(
            varEditMode = "New",
            // --- CREATE ---
            Patch(
                SharePointAppointments.Appointments,
                Defaults(SharePointAppointments.Appointments),
                {
                    Title:           locCustomer.Title & " - " & locProvider.Title,
                    CustomerId:      locCustomer.ID,
                    CustomerName:    locCustomer.Title,
                    ProviderId:      locProvider.ID,
                    ProviderName:    locProvider.Title,
                    AppointmentDate: locDate,
                    StartTime:       locStartTime,
                    EndTime:         Text(TimeValue(locStartTime) + Time(0, locDuration, 0), "HH:MM"),
                    Duration:        locDuration,
                    Status:          "Pending",
                    ServiceType:     locServiceType,
                    Notes:           locNotes,
                    ReminderSent:    false
                }
            ),
            // --- UPDATE ---
            Patch(
                SharePointAppointments.Appointments,
                varSelectedAppointment,
                {
                    Title:           locCustomer.Title & " - " & locProvider.Title,
                    CustomerId:      locCustomer.ID,
                    CustomerName:    locCustomer.Title,
                    ProviderId:      locProvider.ID,
                    ProviderName:    locProvider.Title,
                    AppointmentDate: locDate,
                    StartTime:       locStartTime,
                    EndTime:         Text(TimeValue(locStartTime) + Time(0, locDuration, 0), "HH:MM"),
                    Duration:        locDuration,
                    Status:          locStatus,
                    ServiceType:     locServiceType,
                    Notes:           locNotes
                }
            )
        );
        UpdateContext({ locSaving: false });
        Navigate(HomeScreen, ScreenTransition.Fade)
    )

// ---------------------------------------------------------------------------
// Delete Button  –  btnDelete  (Edit mode only)
// ---------------------------------------------------------------------------
btnDelete.Text     = "Cancel Appointment"
btnDelete.Fill     = ColorValue("#FEF2F2")
btnDelete.Color    = ColorValue("#DC2626")
btnDelete.BorderColor = ColorValue("#DC2626")
btnDelete.Width    = Parent.Width - 48
btnDelete.Height   = 44
btnDelete.X        = 24
btnDelete.Y        = 688
btnDelete.Visible  = varEditMode = "Edit" && varSelectedAppointment.Status <> "Cancelled"

btnDelete.OnSelect =
    If(
        Confirm("Cancel this appointment?"),
        Patch(
            SharePointAppointments.Appointments,
            varSelectedAppointment,
            { Status: "Cancelled" }
        );
        Navigate(HomeScreen, ScreenTransition.Fade)
    )
