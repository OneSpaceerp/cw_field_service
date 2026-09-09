# C-Water Field Service Management (`cw_field_service`)

Custom ERPNext v16 application for C-Water to digitize and manage field service operations, site visits, technical water inspections, engineer GPS verification, and service reporting.

## Key Features
- **Service Requests**: Complete lifecycle management from customer issue intake to supervisor assignment and SLA tracking.
- **Service Locations**: Customer site master records with GPS coordinates, geofence definitions, and installed equipment.
- **Site Visits**: Mobile-ready visit transactions recording check-in/check-out timestamps, GPS coordinates, distance calculations, and geofence verification (`Verified`, `Warning`, `Exception`).
- **Water Quality Inspections**: Configurable technical water parameter readings (pH, TDS, Conductivity, Turbidity, Chlorine, etc.) with real-time range checks against normal/warning/critical thresholds.
- **On-Site Operational Data**: Findings with severity and photo evidence, follow-up actions, equipment/material requirements linked to ERPNext Items, site expenses, and washing/cleaning/CIP logs.
- **Technical Service Report**: Professional customer-ready service reports with branding, parameter tables, findings, and digital signatures.
- **Field Engineer PWA APIs**: REST endpoints supporting authentication, assignment fetching, check-in, offline draft saving, visit submission, and idempotent sync.

## Installation
```bash
bench get-app /path/to/cw_field_service
bench --site erp.cw-eg.com install-app cw_field_service
bench --site erp.cw-eg.com migrate
```

## License
MIT License. Copyright (c) 2026 Nest Software Development & C-Water.
