// =============================================================================
// DayViewScreen.fx  –  All appointments for a selected day (timeline view)
// =============================================================================
// PURPOSE
//   Shows a time-slot grid (08:00 – 18:00) with appointment blocks overlaid.
//   Staff can tap an existing appointment to edit or create a new one at a
//   blank slot.
// =============================================================================

// ---------------------------------------------------------------------------
// Screen variable:  varDayViewDate  (set by CalendarScreen before navigation)
// ---------------------------------------------------------------------------
Screen.OnVisible =
    ClearCollect(
        colDayAppointments,
        SortByColumns(
            Filter(
                SharePointAppointments.Appointments,
                DateValue(Text(AppointmentDate, "yyyy-mm-dd")) = varDayViewDate
                    && Status <> "Cancelled"
            ),
            "StartTime", SortOrder.Ascending
        )
    );
    // Build the 08:00–18:00 hour slots
    ClearCollect(
        colTimeSlots,
        ForAll(
            Sequence(21),           // 21 half-hour slots  08:00 – 18:00
            {
                SlotStart: Text(
                    TimeValue("08:00") + Time(0, (Value - 1) * 30, 0),
                    "HH:MM"
                ),
                SlotHour: Hour(TimeValue("08:00") + Time(0, (Value - 1) * 30, 0))
            }
        )
    )

// ---------------------------------------------------------------------------
// Header
// ---------------------------------------------------------------------------
lblDayHeader.Text  = Text(varDayViewDate, "dddd, mmmm d yyyy")
lblDayHeader.Size  = 17
lblDayHeader.Color = ColorValue("#1A3C5E")
lblDayHeader.X     = 24
lblDayHeader.Y     = 16

btnDayBack.Text     = "← Calendar"
btnDayBack.OnSelect = Navigate(CalendarScreen, ScreenTransition.Back)
btnDayBack.X        = Parent.Width - 128
btnDayBack.Y        = 14

// ---------------------------------------------------------------------------
// Time-slot gallery  –  galTimeline
// ---------------------------------------------------------------------------
galTimeline.Items           = colTimeSlots
galTimeline.X               = 0
galTimeline.Y               = 56
galTimeline.Width           = Parent.Width
galTimeline.Height          = Parent.Height - 56 - 60
galTimeline.Layout          = Layout.Vertical
galTimeline.TemplateSize    = 60   // 60px per 30-minute block
galTimeline.TemplatePadding = 0

// Time label (left gutter)
galTimeline.lblSlotTime.Text  = ThisItem.SlotStart
galTimeline.lblSlotTime.Width = 52
galTimeline.lblSlotTime.X     = 8
galTimeline.lblSlotTime.Color = ColorValue("#9CA3AF")
galTimeline.lblSlotTime.Size  = 11
galTimeline.lblSlotTime.Y     = 4

// Divider line
galTimeline.rectDivider.Height = 1
galTimeline.rectDivider.Width  = Parent.Width - 64
galTimeline.rectDivider.X      = 60
galTimeline.rectDivider.Y      = 0
galTimeline.rectDivider.Fill   = ColorValue("#F3F4F6")

// Appointment block overlay (only visible when an appt starts in this slot)
galTimeline.rectAppt.Fill =
    If(
        !IsEmpty(Filter(colDayAppointments, StartTime = ThisItem.SlotStart)),
        ColorValue("#DBEAFE"),
        RGBA(0,0,0,0)
    )
galTimeline.rectAppt.Width  = Parent.Width - 72
galTimeline.rectAppt.Height =
    With(
        { appt: LookUp(colDayAppointments, StartTime = ThisItem.SlotStart) },
        If(IsBlank(appt), 0, appt.Duration / 30 * 60)
    )
galTimeline.rectAppt.X = 64

galTimeline.lblApptTitle.Text =
    With(
        { appt: LookUp(colDayAppointments, StartTime = ThisItem.SlotStart) },
        If(
            IsBlank(appt),
            "",
            appt.CustomerName & " → " & appt.ProviderName & "  [" & appt.ServiceType & "]"
        )
    )
galTimeline.lblApptTitle.Size  = 12
galTimeline.lblApptTitle.Color = ColorValue("#1D4ED8")
galTimeline.lblApptTitle.X     = 68
galTimeline.lblApptTitle.Y     = 6

// Tap blank slot → new appointment pre-filled with that time
galTimeline.OnSelect =
    With(
        { appt: LookUp(colDayAppointments, StartTime = ThisItem.SlotStart) },
        If(
            IsBlank(appt),
            // New appointment at this slot
            Set(varEditMode, "New");
            Set(varSelectedAppointment, Blank());
            Set(varPreFillDate, varDayViewDate);
            Set(varPreFillTime, ThisItem.SlotStart);
            Navigate(AppointmentFormScreen, ScreenTransition.Fade),
            // Edit existing appointment
            Set(varEditMode, "Edit");
            Set(varSelectedAppointment, appt);
            Navigate(AppointmentFormScreen, ScreenTransition.Fade)
        )
    )

// ---------------------------------------------------------------------------
// Bottom action bar
// ---------------------------------------------------------------------------
btnDayNew.Text     = "+ New Appointment"
btnDayNew.Fill     = ColorValue("#2563EB")
btnDayNew.Color    = Color.White
btnDayNew.Width    = 200
btnDayNew.Height   = 44
btnDayNew.X        = 24
btnDayNew.Y        = Parent.Height - 56
btnDayNew.OnSelect =
    Set(varEditMode, "New");
    Set(varSelectedAppointment, Blank());
    Set(varPreFillDate, varDayViewDate);
    Set(varPreFillTime, "09:00");
    Navigate(AppointmentFormScreen, ScreenTransition.Fade)
