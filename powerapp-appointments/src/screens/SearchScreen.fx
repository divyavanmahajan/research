// =============================================================================
// SearchScreen.fx  –  Search & Filter appointments
// =============================================================================
// PURPOSE
//   Full-text search across customer name, provider name, notes, and
//   service type. Also supports filtering by status and date range.
// =============================================================================

Screen.OnVisible =
    UpdateContext({
        locSearchText:   "",
        locFilterStatus: "All",
        locFromDate:     DateAdd(Today(), -30, TimeUnit.Days),
        locToDate:       DateAdd(Today(),  30, TimeUnit.Days)
    });
    ClearCollect(colSearchResults, SharePointAppointments.Appointments)

// ---------------------------------------------------------------------------
// Search bar  –  txtSearch
// ---------------------------------------------------------------------------
txtSearch.HintText    = "Search customer, provider, notes…"
txtSearch.Y           = 24
txtSearch.X           = 24
txtSearch.Width       = Parent.Width - 48
txtSearch.OnChange    = UpdateContext({ locSearchText: txtSearch.Text })

// ---------------------------------------------------------------------------
// Status filter chips  (rendered as a horizontal gallery)
// ---------------------------------------------------------------------------
galStatusChips.Items = ["All","Pending","Confirmed","Completed","Cancelled","NoShow"]
galStatusChips.Layout = Layout.Horizontal
galStatusChips.TemplateSize = 90
galStatusChips.TemplatePadding = 4
galStatusChips.Height = 40
galStatusChips.Y      = 72

galStatusChips.btnChip.Text  = ThisItem.Value
galStatusChips.btnChip.Fill  =
    If(ThisItem.Value = locFilterStatus, ColorValue("#2563EB"), ColorValue("#F3F4F6"))
galStatusChips.btnChip.Color =
    If(ThisItem.Value = locFilterStatus, Color.White, ColorValue("#374151"))
galStatusChips.btnChip.BorderRadius = 20
galStatusChips.btnChip.OnSelect = UpdateContext({ locFilterStatus: ThisItem.Value })

// ---------------------------------------------------------------------------
// Date range pickers
// ---------------------------------------------------------------------------
lblFromDate.Text = "From"
lblFromDate.Y    = 124

dtpFrom.DefaultDate = locFromDate
dtpFrom.Y           = 144
dtpFrom.X           = 24
dtpFrom.Width       = (Parent.Width / 2) - 32
dtpFrom.OnChange    = UpdateContext({ locFromDate: dtpFrom.SelectedDate })

lblToDate.Text = "To"
lblToDate.Y    = 124
lblToDate.X    = Parent.Width / 2

dtpTo.DefaultDate = locToDate
dtpTo.Y           = 144
dtpTo.X           = Parent.Width / 2
dtpTo.Width       = (Parent.Width / 2) - 24
dtpTo.OnChange    = UpdateContext({ locToDate: dtpTo.SelectedDate })

// ---------------------------------------------------------------------------
// Results gallery  –  galResults
// ---------------------------------------------------------------------------
// Computed filtered collection (referenced as Items)
galResults.Items =
    SortByColumns(
        Filter(
            colSearchResults,
            // Text search
            (locSearchText = ""
                || CustomerName  in locSearchText
                || ProviderName  in locSearchText
                || Notes         in locSearchText
                || ServiceType   in locSearchText),
            // Status filter
            locFilterStatus = "All" || Status = locFilterStatus,
            // Date range
            AppointmentDate >= locFromDate,
            AppointmentDate <= locToDate
        ),
        "AppointmentDate", SortOrder.Descending,
        "StartTime",       SortOrder.Descending
    )

galResults.X              = 0
galResults.Y              = 204
galResults.Width          = Parent.Width
galResults.Height         = Parent.Height - 204
galResults.Layout         = Layout.Vertical
galResults.TemplateSize   = 80
galResults.TemplatePadding = 8

// Row layout (same as HomeScreen gallery)
galResults.lblDate.Text   = Text(ThisItem.AppointmentDate, "mmm d") & " · " & ThisItem.StartTime
galResults.lblDate.Color  = ColorValue("#1D4ED8")
galResults.lblDate.Size   = 12

galResults.lblSummary.Text  = ThisItem.CustomerName & "  →  " & ThisItem.ProviderName
galResults.lblSummary.Size  = 14

galResults.lblService.Text  = ThisItem.ServiceType & " · " & ThisItem.Duration & " min"
galResults.lblService.Size  = 11
galResults.lblService.Color = ColorValue("#6B7280")

galResults.lblStatus.Text  = ThisItem.Status
galResults.lblStatus.Color = Switch(
    ThisItem.Status,
    "Confirmed", ColorValue("#059669"),
    "Pending",   ColorValue("#D97706"),
    "Cancelled", ColorValue("#DC2626"),
    "Completed", ColorValue("#6B7280"),
    Color.Black
)

galResults.OnSelect =
    Set(varSelectedAppointment, ThisItem);
    Set(varEditMode, "Edit");
    Navigate(AppointmentFormScreen, ScreenTransition.Fade)

// ---------------------------------------------------------------------------
// Result count label
// ---------------------------------------------------------------------------
lblResultCount.Text  = CountRows(galResults.AllItems) & " results"
lblResultCount.Y     = 180
lblResultCount.X     = 24
lblResultCount.Color = ColorValue("#6B7280")
lblResultCount.Size  = 12
