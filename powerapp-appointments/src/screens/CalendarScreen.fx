// =============================================================================
// CalendarScreen.fx  –  Monthly / Weekly Calendar View
// =============================================================================
// PURPOSE
//   Visual calendar grid letting staff browse appointments by day.
//   Tapping a day cell navigates to DayViewScreen for that date.
// =============================================================================

// ---------------------------------------------------------------------------
// Screen variables
//   locViewMonth   – first day of the displayed month (Date value)
//   locSelectedDay – the day the user tapped (Date value)
// ---------------------------------------------------------------------------
Screen.OnVisible =
    UpdateContext({
        locViewMonth:   Date(Year(Today()), Month(Today()), 1),
        locSelectedDay: Today()
    });
    // Load full month appointments
    ClearCollect(
        colMonthAppointments,
        Filter(
            SharePointAppointments.Appointments,
            Year(AppointmentDate)  = Year(locViewMonth),
            Month(AppointmentDate) = Month(locViewMonth),
            Status <> "Cancelled"
        )
    )

// ---------------------------------------------------------------------------
// Month navigation header
// ---------------------------------------------------------------------------
lblMonthYear.Text  = Text(locViewMonth, "mmmm yyyy")
lblMonthYear.Size  = 18
lblMonthYear.Color = ColorValue("#1A3C5E")
lblMonthYear.X     = Parent.Width / 2 - 80
lblMonthYear.Y     = 16

btnPrevMonth.Text     = "‹"
btnPrevMonth.Size     = 24
btnPrevMonth.X        = 16
btnPrevMonth.Y        = 12
btnPrevMonth.OnSelect =
    UpdateContext({
        locViewMonth: DateAdd(locViewMonth, -1, TimeUnit.Months)
    });
    ClearCollect(
        colMonthAppointments,
        Filter(
            SharePointAppointments.Appointments,
            Year(AppointmentDate)  = Year(locViewMonth),
            Month(AppointmentDate) = Month(locViewMonth),
            Status <> "Cancelled"
        )
    )

btnNextMonth.Text     = "›"
btnNextMonth.Size     = 24
btnNextMonth.X        = Parent.Width - 48
btnNextMonth.Y        = 12
btnNextMonth.OnSelect =
    UpdateContext({
        locViewMonth: DateAdd(locViewMonth, 1, TimeUnit.Months)
    });
    ClearCollect(
        colMonthAppointments,
        Filter(
            SharePointAppointments.Appointments,
            Year(AppointmentDate)  = Year(locViewMonth),
            Month(AppointmentDate) = Month(locViewMonth),
            Status <> "Cancelled"
        )
    )

// ---------------------------------------------------------------------------
// Weekday header row  (Sun – Sat labels)
// ---------------------------------------------------------------------------
// Each label is positioned at X = colIndex * cellWidth + offsetX
// cellWidth  = Parent.Width / 7
// Row height = 32,  Y = 56
//
// In Power Apps Studio add 7 labels with texts:
//   "Sun","Mon","Tue","Wed","Thu","Fri","Sat"
// and distribute them evenly across the top.

// ---------------------------------------------------------------------------
// Calendar day grid  –  galCalendar
// ---------------------------------------------------------------------------
// The gallery uses a 42-item sequence (6 weeks × 7 days) built as a collection.

// Helper collection built when month changes (also call in OnVisible):
ClearCollect(colCalendarDays,
    // Build a sequence of 42 dates starting on the Sunday of the week
    // containing the 1st of locViewMonth
    ForAll(
        Sequence(42),
        {
            CalDate: DateAdd(
                // Start of calendar grid = first Sunday on or before 1st of month
                DateAdd(locViewMonth, -(Weekday(locViewMonth, StartOfWeek.Sunday) - 1), TimeUnit.Days),
                Value - 1,
                TimeUnit.Days
            ),
            DayNum: Day(
                DateAdd(
                    DateAdd(locViewMonth, -(Weekday(locViewMonth, StartOfWeek.Sunday) - 1), TimeUnit.Days),
                    Value - 1, TimeUnit.Days
                )
            )
        }
    )
)

galCalendar.Items          = colCalendarDays
galCalendar.X              = 0
galCalendar.Y              = 88
galCalendar.Width          = Parent.Width
galCalendar.Height         = Parent.Height - 88 - 64
galCalendar.WrapCount      = 7        // 7 columns
galCalendar.Layout         = Layout.Grid
galCalendar.TemplatePadding = 2
galCalendar.TemplateSize   = (Parent.Height - 88 - 64) / 6   // 6 rows

// Cell: background tint
galCalendar.rectCell.Fill =
    If(
        Month(ThisItem.CalDate) <> Month(locViewMonth), ColorValue("#F9FAFB"),  // grayed out (other month)
        ThisItem.CalDate = Today(),                      ColorValue("#DBEAFE"),  // today
        ThisItem.CalDate = locSelectedDay,               ColorValue("#EDE9FE"),  // selected
        Color.White
    )
galCalendar.rectCell.BorderColor = ColorValue("#E5E7EB")
galCalendar.rectCell.BorderThickness = 1

// Cell: day number label
galCalendar.lblDay.Text  = Text(ThisItem.DayNum)
galCalendar.lblDay.Color =
    If(
        Month(ThisItem.CalDate) <> Month(locViewMonth),
        ColorValue("#D1D5DB"),   // muted
        ColorValue("#1F2937")    // normal
    )
galCalendar.lblDay.Size  = 12
galCalendar.lblDay.X     = 4
galCalendar.lblDay.Y     = 4

// Cell: appointment count dot
galCalendar.lblDot.Text  =
    If(
        CountRows(Filter(colMonthAppointments,
            DateValue(Text(AppointmentDate,"yyyy-mm-dd")) = ThisItem.CalDate
        )) > 0,
        "●",
        ""
    )
galCalendar.lblDot.Color = ColorValue("#2563EB")
galCalendar.lblDot.Size  = 8
galCalendar.lblDot.Y     = galCalendar.TemplateSize - 16

// Cell: tap action
galCalendar.OnSelect =
    UpdateContext({ locSelectedDay: ThisItem.CalDate });
    Set(varDayViewDate, ThisItem.CalDate);
    Navigate(DayViewScreen, ScreenTransition.Fade)

// ---------------------------------------------------------------------------
// Bottom action bar
// ---------------------------------------------------------------------------
btnNewAppt.Text     = "+ New"
btnNewAppt.Fill     = ColorValue("#2563EB")
btnNewAppt.Color    = Color.White
btnNewAppt.Width    = 120
btnNewAppt.Height   = 44
btnNewAppt.X        = 24
btnNewAppt.Y        = Parent.Height - 56
btnNewAppt.OnSelect =
    Set(varEditMode, "New");
    Set(varSelectedAppointment, Blank());
    Navigate(AppointmentFormScreen, ScreenTransition.Fade)

btnBackHome.Text     = "Home"
btnBackHome.Fill     = ColorValue("#F3F4F6")
btnBackHome.Color    = ColorValue("#374151")
btnBackHome.Width    = 100
btnBackHome.Height   = 44
btnBackHome.X        = Parent.Width - 124
btnBackHome.Y        = Parent.Height - 56
btnBackHome.OnSelect = Navigate(HomeScreen, ScreenTransition.Back)
