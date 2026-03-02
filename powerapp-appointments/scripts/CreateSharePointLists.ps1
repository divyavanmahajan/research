# =============================================================================
# CreateSharePointLists.ps1
# =============================================================================
# PURPOSE
#   Creates the three SharePoint lists (Appointments, Providers, Customers)
#   with all required columns on a target site.
#
# PREREQUISITES
#   PnP.PowerShell module:
#     Install-Module -Name PnP.PowerShell -Scope CurrentUser
#
# USAGE
#   .\CreateSharePointLists.ps1 -SiteUrl "https://<tenant>.sharepoint.com/sites/Appointments"
# =============================================================================

param(
    [Parameter(Mandatory=$true)]
    [string]$SiteUrl
)

# Connect (will prompt for browser login)
Connect-PnPOnline -Url $SiteUrl -UseWebLogin

Write-Host "Connected to $SiteUrl" -ForegroundColor Cyan

# =============================================================================
# Helper function
# =============================================================================
function Add-ListIfNotExists {
    param([string]$ListName, [string]$ListTitle)
    $existing = Get-PnPList -Identity $ListName -ErrorAction SilentlyContinue
    if ($null -eq $existing) {
        New-PnPList -Title $ListTitle -Template GenericList -Url "Lists/$ListName"
        Write-Host "  Created list: $ListTitle" -ForegroundColor Green
    } else {
        Write-Host "  List already exists: $ListTitle" -ForegroundColor Yellow
    }
    return Get-PnPList -Identity $ListName
}

function Add-ColumnIfNotExists {
    param([string]$ListName, [string]$FieldXml)
    try {
        Add-PnPFieldFromXml -List $ListName -FieldXml $FieldXml | Out-Null
    } catch {
        # Column already exists – ignore
    }
}

# =============================================================================
# 1. Appointments list
# =============================================================================
Write-Host "`nCreating Appointments list..." -ForegroundColor Cyan
Add-ListIfNotExists -ListName "Appointments" -ListTitle "Appointments"

$apptColumns = @(
    '<Field Type="Number"   DisplayName="CustomerId"     Name="CustomerId"     Required="TRUE" />',
    '<Field Type="Text"     DisplayName="CustomerName"   Name="CustomerName"   Required="TRUE" MaxLength="255" />',
    '<Field Type="Number"   DisplayName="ProviderId"     Name="ProviderId"     Required="TRUE" />',
    '<Field Type="Text"     DisplayName="ProviderName"   Name="ProviderName"   Required="TRUE" MaxLength="255" />',
    '<Field Type="DateTime" DisplayName="AppointmentDate" Name="AppointmentDate" Required="TRUE" />',
    '<Field Type="Text"     DisplayName="StartTime"      Name="StartTime"      Required="TRUE" MaxLength="5" />',
    '<Field Type="Text"     DisplayName="EndTime"        Name="EndTime"        Required="FALSE" MaxLength="5" />',
    '<Field Type="Number"   DisplayName="Duration"       Name="Duration"       Required="TRUE" Min="15" Max="480" />',
    '<Field Type="Choice"   DisplayName="Status"         Name="Status"         Required="TRUE">
       <Default>Pending</Default>
       <CHOICES><CHOICE>Pending</CHOICE><CHOICE>Confirmed</CHOICE><CHOICE>Cancelled</CHOICE><CHOICE>Completed</CHOICE><CHOICE>NoShow</CHOICE></CHOICES>
     </Field>',
    '<Field Type="Choice"   DisplayName="ServiceType"    Name="ServiceType"    Required="TRUE">
       <Default>Consultation</Default>
       <CHOICES><CHOICE>Consultation</CHOICE><CHOICE>FollowUp</CHOICE><CHOICE>Procedure</CHOICE><CHOICE>Review</CHOICE><CHOICE>Other</CHOICE></CHOICES>
     </Field>',
    '<Field Type="Note"     DisplayName="Notes"          Name="Notes"          Required="FALSE" NumLines="6" />',
    '<Field Type="Boolean"  DisplayName="ReminderSent"   Name="ReminderSent"   Required="FALSE"><Default>0</Default></Field>'
)

foreach ($xml in $apptColumns) {
    Add-ColumnIfNotExists -ListName "Appointments" -FieldXml $xml
}
Write-Host "  Appointments columns created." -ForegroundColor Green

# =============================================================================
# 2. Providers list
# =============================================================================
Write-Host "`nCreating Providers list..." -ForegroundColor Cyan
Add-ListIfNotExists -ListName "Providers" -ListTitle "Providers"

$providerColumns = @(
    '<Field Type="Text"    DisplayName="Email"                  Name="ProviderEmail"          Required="TRUE"  MaxLength="255" />',
    '<Field Type="Text"    DisplayName="Department"             Name="Department"             Required="FALSE" MaxLength="100" />',
    '<Field Type="Text"    DisplayName="Specialty"              Name="Specialty"              Required="FALSE" MaxLength="100" />',
    '<Field Type="Boolean" DisplayName="IsActive"               Name="IsActive"               Required="FALSE"><Default>1</Default></Field>',
    '<Field Type="Number"  DisplayName="MaxDailyAppointments"   Name="MaxDailyAppointments"   Required="FALSE" Min="1" Max="100"><Default>10</Default></Field>',
    '<Field Type="Number"  DisplayName="DefaultDuration"        Name="DefaultDuration"        Required="FALSE" Min="15" Max="120"><Default>30</Default></Field>'
)

foreach ($xml in $providerColumns) {
    Add-ColumnIfNotExists -ListName "Providers" -FieldXml $xml
}
Write-Host "  Providers columns created." -ForegroundColor Green

# =============================================================================
# 3. Customers list
# =============================================================================
Write-Host "`nCreating Customers list..." -ForegroundColor Cyan
Add-ListIfNotExists -ListName "Customers" -ListTitle "Customers"

$customerColumns = @(
    '<Field Type="Text"     DisplayName="Email"       Name="CustomerEmail"  Required="FALSE" MaxLength="255" />',
    '<Field Type="Text"     DisplayName="Phone"       Name="Phone"          Required="FALSE" MaxLength="30"  />',
    '<Field Type="DateTime" DisplayName="DateOfBirth" Name="DateOfBirth"    Required="FALSE" />',
    '<Field Type="Note"     DisplayName="Notes"       Name="CustomerNotes"  Required="FALSE" NumLines="4"   />',
    '<Field Type="Boolean"  DisplayName="IsActive"    Name="IsActive"       Required="FALSE"><Default>1</Default></Field>'
)

foreach ($xml in $customerColumns) {
    Add-ColumnIfNotExists -ListName "Customers" -FieldXml $xml
}
Write-Host "  Customers columns created." -ForegroundColor Green

# =============================================================================
# 4. Seed sample data
# =============================================================================
Write-Host "`nSeeding sample data..." -ForegroundColor Cyan

# Provider
Add-PnPListItem -List "Providers" -Values @{
    Title                 = "Dr. Sarah Patel"
    ProviderEmail         = "sarah.patel@example.com"
    Department            = "General Medicine"
    Specialty             = "Internal Medicine"
    IsActive              = $true
    MaxDailyAppointments  = 12
    DefaultDuration       = 30
} | Out-Null

# Customer
Add-PnPListItem -List "Customers" -Values @{
    Title         = "Alice Johnson"
    CustomerEmail = "alice.johnson@example.com"
    Phone         = "555-0101"
    IsActive      = $true
} | Out-Null

Write-Host "  Sample Provider and Customer seeded." -ForegroundColor Green

Write-Host "`nSetup complete. Open Power Apps Studio to build the canvas app." -ForegroundColor Cyan
Disconnect-PnPOnline
