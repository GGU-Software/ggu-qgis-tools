# CLI `create` Command Proposal

## Overview

Add a new `create` subcommand to ggu-connect CLI that creates database entities from XML input.
This reuses the existing XML import infrastructure (`IConnectXMLImporter` → `TMergeHelper`).

## Command Syntax

```bash
ggu-connect create drillings --input <xml-file> --db-profile <profile> [options]
```

## XML Input Structure

Uses the existing GGU-CONNECT XML format:

```xml
<?xml version="1.0" encoding="utf-8"?>
<ggu-connect version="1.0">
  <project id="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx">
    <drillings>
      <drilling name="BH-001"
                location-id="new-guid-1"
                x-coordinate="357812.12"
                y-coordinate="5812341.44"
                z-coordinate-begin="45.50"
                coordinatesystem-epsg-code="25832">
      </drilling>
    </drillings>
    <cone-penetrations>
      <cone-penetration name="CPT-001"
                        location-id="new-guid-2"
                        x-coordinate="357815.00"
                        y-coordinate="5812345.00"
                        coordinatesystem-epsg-code="25832">
      </cone-penetration>
    </cone-penetrations>
    <percussion-drillings>
      <percussion-drilling name="DPT-001"
                           location-id="new-guid-3"
                           x-coordinate="357820.00"
                           y-coordinate="5812350.00"
                           coordinatesystem-epsg-code="25832">
      </percussion-drilling>
    </percussion-drillings>
  </project>
</ggu-connect>
```

## Supported Drilling Types

| XML Element | Description |
|-------------|-------------|
| `<drilling>` | Standard borehole (Bohrung) |
| `<cone-penetration>` | Cone Penetration Test / CPT (Drucksondierung) |
| `<percussion-drilling>` | Dynamic Probing Test / DPT (Rammsondierung) |

## CLI Options

```
OPTIONS:
  -i, --input <file>     Input XML file path (required)
  -p, --db-profile       Database profile name
      --db <conn>        Direct database connection string
      --dry-run          Validate and preview without creating
      --project <guid>   Target project GUID (overrides XML)
```

## Implementation

Reuses existing infrastructure:

```
XML File → IConnectXMLImporter.importProjectsFromXmlFile()
                    ↓
              IList<IProject>
                    ↓
         TMergeHelper.Create(dbContext, projects, false)
                    ↓
         TMergeHelper.DryRun() → Conflict detection
                    ↓
         TMergeHelper.doMerge() → SQL INSERT statements
```

### Key Components (all existing)

| Component | Location |
|-----------|----------|
| `IConnectXMLImporter` | `GGU.Libs.Connect.XML.pas` |
| `IConnectModelFactory` | `GGU.Libs.Connect.Model.Intf.pas` |
| `TMergeHelper` | `GGU.Libs.Connect.Impl.Merge.pas` |

### New CLI Command Handler

```
apps-desktop/ggu-connect-cli/
└── src/Commands/
    └── GGU.Apps.ConnectCLI.Commands.Create.pas  # New CLI command
```

## QGIS Plugin Integration

The QGIS plugin creates XML and calls the CLI:

```python
def create_drillings(self, points, drilling_type, project_id, db_profile):
    # Build XML
    xml_content = self._build_drilling_xml(points, drilling_type, project_id)

    # Write to temp file
    with open(temp_file, 'w', encoding='utf-8') as f:
        f.write(xml_content)

    # Call CLI
    result = subprocess.run([
        cli_path, "create", "drillings",
        "--input", temp_file,
        "--db-profile", db_profile
    ])
```

## Example Usage

```bash
# Create drillings from XML file
ggu-connect create drillings --input new-boreholes.xml --db-profile production

# Dry run to validate
ggu-connect create drillings --input new-boreholes.xml --db-profile production --dry-run
```

## Benefits

1. **No new format** - Reuses existing XML schema
2. **Proven infrastructure** - Battle-tested merge logic
3. **Transaction support** - Atomic operations with rollback
4. **Full entity support** - Can create any entity type supported by XML
