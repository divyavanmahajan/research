// =============================================================================
// StatusBadge.fx  –  Reusable status badge component
// =============================================================================
// PURPOSE
//   Renders a coloured pill badge for an appointment status string.
//
// COMPONENT PROPERTIES (inputs):
//   StatusValue  (Text)  – one of Pending / Confirmed / Cancelled / Completed / NoShow
// =============================================================================

Component.StatusValue.Default = "Pending"

// Pill background rectangle
rectBadge.Width         = lblBadgeText.Width + 16
rectBadge.Height        = 24
rectBadge.BorderRadius  = 12
rectBadge.Fill          = Switch(
    Component.StatusValue,
    "Confirmed", ColorValue("#D1FAE5"),
    "Pending",   ColorValue("#FEF3C7"),
    "Cancelled", ColorValue("#FEE2E2"),
    "Completed", ColorValue("#F3F4F6"),
    "NoShow",    ColorValue("#FDE8D8"),
    ColorValue("#F3F4F6")
)

// Status text
lblBadgeText.Text  = Component.StatusValue
lblBadgeText.Color = Switch(
    Component.StatusValue,
    "Confirmed", ColorValue("#065F46"),
    "Pending",   ColorValue("#92400E"),
    "Cancelled", ColorValue("#991B1B"),
    "Completed", ColorValue("#374151"),
    "NoShow",    ColorValue("#9A3412"),
    ColorValue("#374151")
)
lblBadgeText.Size   = 11
lblBadgeText.Font   = Font.'Open Sans'
lblBadgeText.X      = 8
lblBadgeText.Y      = 4
lblBadgeText.Height = 16
