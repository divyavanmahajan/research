// =============================================================================
// NavBar.fx  –  Reusable bottom navigation bar component
// =============================================================================
// PURPOSE
//   Persistent bottom tab bar shared across all primary screens.
//   Import as a Component in Power Apps Studio.
//
// COMPONENT PROPERTIES (inputs):
//   ActiveScreen  (Text, default "Home")  – highlights the active tab
// =============================================================================

// Component input property
Component.ActiveScreen.Default = "Home"

// ---------------------------------------------------------------------------
// Background strip
// ---------------------------------------------------------------------------
rectNavBg.Fill         = Color.White
rectNavBg.BorderColor  = ColorValue("#E5E7EB")
rectNavBg.BorderThickness = 1      // top border only via Y positioning
rectNavBg.Height       = 56
rectNavBg.Width        = Parent.Width
rectNavBg.X            = 0
rectNavBg.Y            = 0

// ---------------------------------------------------------------------------
// Tab: Home
// ---------------------------------------------------------------------------
btnNavHome.Text   = If(Component.ActiveScreen = "Home", "🏠 Home", "Home")
btnNavHome.Width  = Parent.Width / 4
btnNavHome.Height = 56
btnNavHome.X      = 0
btnNavHome.Y      = 0
btnNavHome.Fill   = RGBA(0,0,0,0)
btnNavHome.Color  =
    If(Component.ActiveScreen = "Home", ColorValue("#2563EB"), ColorValue("#6B7280"))
btnNavHome.OnSelect = Navigate(HomeScreen, ScreenTransition.None)

// ---------------------------------------------------------------------------
// Tab: Calendar
// ---------------------------------------------------------------------------
btnNavCalendar.Text   = If(Component.ActiveScreen = "Calendar", "📅 Calendar", "Calendar")
btnNavCalendar.Width  = Parent.Width / 4
btnNavCalendar.Height = 56
btnNavCalendar.X      = Parent.Width / 4
btnNavCalendar.Y      = 0
btnNavCalendar.Fill   = RGBA(0,0,0,0)
btnNavCalendar.Color  =
    If(Component.ActiveScreen = "Calendar", ColorValue("#2563EB"), ColorValue("#6B7280"))
btnNavCalendar.OnSelect = Navigate(CalendarScreen, ScreenTransition.None)

// ---------------------------------------------------------------------------
// Tab: Search
// ---------------------------------------------------------------------------
btnNavSearch.Text   = If(Component.ActiveScreen = "Search", "🔍 Search", "Search")
btnNavSearch.Width  = Parent.Width / 4
btnNavSearch.Height = 56
btnNavSearch.X      = Parent.Width / 2
btnNavSearch.Y      = 0
btnNavSearch.Fill   = RGBA(0,0,0,0)
btnNavSearch.Color  =
    If(Component.ActiveScreen = "Search", ColorValue("#2563EB"), ColorValue("#6B7280"))
btnNavSearch.OnSelect = Navigate(SearchScreen, ScreenTransition.None)

// ---------------------------------------------------------------------------
// Tab: New Appointment
// ---------------------------------------------------------------------------
btnNavNew.Text   = "+ New"
btnNavNew.Width  = Parent.Width / 4
btnNavNew.Height = 56
btnNavNew.X      = 3 * Parent.Width / 4
btnNavNew.Y      = 0
btnNavNew.Fill   = RGBA(0,0,0,0)
btnNavNew.Color  = ColorValue("#2563EB")
btnNavNew.OnSelect =
    Set(varEditMode, "New");
    Set(varSelectedAppointment, Blank());
    Navigate(AppointmentFormScreen, ScreenTransition.Fade)
