# CLI `create` Command Proposal

## Overview

Add a new `create` subcommand to ggu-connect CLI that creates database entities from JSON input.
This provides a flexible, extensible interface for creating boreholes, soundings, and other objects.

## Command Syntax

```bash
ggu-connect create --input <json-file> --db-profile <profile> [options]

# Or with inline JSON (for simple cases):
ggu-connect create --json '<json-string>' --db-profile <profile>
```

## JSON Input Structure

### Create Boreholes/Drillings

```json
{
  "operation": "create_drillings",
  "project_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "drillings": [
    {
      "name": "BH-001",
      "type": "borehole",
      "x": 357812.12,
      "y": 5812341.44,
      "z": 45.50,
      "crs": "EPSG:25832",
      "external_id": "EXT-001",
      "date_begin": "2026-01-15",
      "date_end": "2026-01-16",
      "attributes": {
        "contractor": "Drilling Co.",
        "method": "rotary"
      }
    },
    {
      "name": "CPT-001",
      "type": "cpt",
      "x": 357815.00,
      "y": 5812345.00,
      "crs": "EPSG:25832"
    }
  ]
}
```

### Supported Drilling Types

| Type | Description |
|------|-------------|
| `borehole` | Standard borehole (Bohrung) |
| `cpt` | Cone Penetration Test (Drucksondierung) |
| `dpt` | Dynamic Probing Test (Rammsondierung) |
| `trial_pit` | Trial pit / test pit (Schürfgrube) |

### Create Project (Optional)

```json
{
  "operation": "create_project",
  "project": {
    "name": "New Project 2026",
    "project_no": "P-2026-001",
    "customer": "Customer Name",
    "location": "Berlin",
    "attributes": {
      "phase": "exploration"
    }
  }
}
```

## CLI Options

```
OPTIONS:
  -i, --input <file>     Input JSON file path (required unless --json used)
  -j, --json <string>    Inline JSON string (alternative to --input)
  -p, --db-profile       Database profile name
      --db <conn>        Direct database connection string
      --dry-run          Validate and preview without creating
  -f, --output-format    Output format: json (default), text
      --return-ids       Return created entity IDs in output
```

## Output

### Success Response (JSON)

```json
{
  "success": true,
  "created": {
    "drillings": [
      {
        "name": "BH-001",
        "location_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
        "status": "created"
      },
      {
        "name": "CPT-001",
        "location_id": "yyyyyyyy-yyyy-yyyy-yyyy-yyyyyyyyyyyy",
        "status": "created"
      }
    ]
  },
  "summary": {
    "total": 2,
    "created": 2,
    "skipped": 0,
    "errors": 0
  }
}
```

### Error Response

```json
{
  "success": false,
  "errors": [
    {
      "index": 0,
      "name": "BH-001",
      "error": "Duplicate name in project"
    }
  ]
}
```

## Implementation Notes

### Delphi Unit Structure

```
GGU.Apps.ConnectCLI/
├── Commands/
│   ├── CreateCommand.pas        # Main create command handler
│   ├── CreateDrillingsHandler.pas  # Drilling creation logic
│   └── CreateProjectHandler.pas    # Project creation logic
└── Models/
    └── CreateInputModels.pas    # JSON deserialization models
```

### Key Classes

```pascal
type
  TCreateDrillingInput = class
  private
    FName: string;
    FType: string;  // 'borehole', 'cpt', 'dpt', 'trial_pit'
    FX: Double;
    FY: Double;
    FZ: Double;
    FCRS: string;
    FExternalID: string;
    FDateBegin: TDateTime;
    FDateEnd: TDateTime;
  public
    property Name: string read FName write FName;
    property DrillingType: string read FType write FType;
    property X: Double read FX write FX;
    property Y: Double read FY write FY;
    property Z: Double read FZ write FZ;
    property CRS: string read FCRS write FCRS;
    property ExternalID: string read FExternalID write FExternalID;
    property DateBegin: TDateTime read FDateBegin write FDateBegin;
    property DateEnd: TDateTime read FDateEnd write FDateEnd;
  end;

  TCreateDrillingsOperation = class
  private
    FProjectID: TGUID;
    FDrillings: TObjectList<TCreateDrillingInput>;
  public
    property ProjectID: TGUID read FProjectID write FProjectID;
    property Drillings: TObjectList<TCreateDrillingInput> read FDrillings;
  end;
```

### Coordinate Transformation

The command should handle CRS transformation internally:
1. Parse input CRS (e.g., "EPSG:25832")
2. Store coordinates in database native format
3. Use existing `TCoordinateTransformer` if available

### Validation Rules

1. **Required fields**: name, x, y, crs
2. **Unique constraint**: name must be unique within project
3. **CRS validation**: must be valid EPSG code
4. **Type validation**: must be known drilling type

## QGIS Plugin Integration

The QGIS plugin would create JSON like:

```python
def _create_drilling(self, drilling_type):
    # ... collect points from selection ...

    json_data = {
        "operation": "create_drillings",
        "project_id": project_id,
        "drillings": [
            {
                "name": p["name"],
                "type": drilling_type,
                "x": p["x"],
                "y": p["y"],
                "crs": crs,
            }
            for p in points
        ]
    }

    # Write to temp file
    with open(temp_file, 'w') as f:
        json.dump(json_data, f)

    # Call CLI
    subprocess.run([cli_path, "create", "--input", temp_file, "--db-profile", profile])
```

## Future Extensions

The JSON structure supports future operations:

```json
{"operation": "create_soil_layers", ...}
{"operation": "create_samples", ...}
{"operation": "create_groundwater_levels", ...}
{"operation": "update_drillings", ...}
```

## Example Usage

```bash
# Create from file
ggu-connect create --input new-boreholes.json --db-profile production

# Dry run to validate
ggu-connect create --input new-boreholes.json --db-profile production --dry-run

# Inline JSON for single borehole
ggu-connect create --db-profile production --json '{
  "operation": "create_drillings",
  "project_id": "...",
  "drillings": [{"name": "BH-TEST", "type": "borehole", "x": 357812, "y": 5812341, "crs": "EPSG:25832"}]
}'
```
