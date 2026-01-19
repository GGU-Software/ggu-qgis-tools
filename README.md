# GGU QGIS Tools

QGIS Plugin for integration with **GGU-CONNECT CLI** - enables opening boreholes in GGU-STRATIG and creating new boreholes from planning points.

## Features

- **Open in GGU-STRATIG**: Select boreholes in QGIS and open them directly in GGU-STRATIG
- **Create Borehole**: Create new boreholes in GGU-CONNECT from selected planning points
- **Create Sounding**: Create new soundings (CPT) from selected planning points

## Requirements

- QGIS 3.28 or later (tested with 3.44)
- GGU-CONNECT CLI (`GGU.Apps.ConnectCLI.exe`)
- GGU-CONNECT database (PostgreSQL/PostGIS or Access)

## Installation

### From ZIP File

1. Download the latest release ZIP from [Releases](https://github.com/GGU-Software/ggu-qgis-tools/releases)
2. In QGIS: **Sketcher** → **Manage and Install Plugins** → **Install from ZIP**
3. Select the downloaded ZIP file

### Manual Installation

1. Copy the `ggu-qgis-plugin` folder to your QGIS plugins directory:
   - Windows: `%APPDATA%\QGIS\QGIS3\profiles\default\python\plugins\`
   - Linux: `~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/`
   - macOS: `~/Library/Application Support/QGIS/QGIS3/profiles/default/python/plugins/`

2. Restart QGIS

3. Enable the plugin: **Sketcher** → **Manage and Install Plugins** → Search for "GGU"

## Configuration

After installing, configure the plugin:

1. Click the **Settings** button in the GGU Tools toolbar
2. Set the path to `GGU.Apps.ConnectCLI.exe`
3. Select your database profile
4. (Optional) Set a default project ID for creating new boreholes

## Usage

### Open Boreholes in GGU-STRATIG

1. Load a layer from `vw_qgis_borehole_summary` view
2. Select one or more boreholes
3. Click **Open in GGU-STRATIG** in the toolbar

The plugin reads the `LocationID` and `ProjectID` attributes and calls the CLI to open the boreholes.

### Create New Boreholes

1. Select planning points from any point layer
2. Click **Create Borehole** or **Create Sounding**
3. The plugin creates a temporary CSV with coordinates and calls the CLI import

## Layer Requirements

### For Opening Boreholes

The layer must have these attributes (from `vw_qgis_borehole_summary`):
- `LocationID` - Borehole GUID
- `ProjectID` - Project GUID

### For Creating Boreholes

Any point layer works. Optional attributes:
- `name` or `BoreholeName` - Name for the new borehole

## CLI Commands Used

The plugin calls these GGU-CONNECT CLI commands:

```bash
# Open boreholes in STRATIG
ggu-connect export ggu-app --app stratig --mode open \
  --project <ProjectID> --filter-drilling-ids <LocationIDs> \
  --db-profile <profile> --output <temp_dir>

# Create boreholes from coordinates
ggu-connect import coordinates --input <csv_file> \
  --project <ProjectID> --db-profile <profile> \
  --col-name 0 --col-x 1 --col-y 2 --start-row 2
```

## Development

### Project Structure

```
ggu-qgis-tools/
├── README.md
├── LICENSE
├── .gitignore
└── ggu-qgis-plugin/
    ├── __init__.py
    ├── metadata.txt
    ├── plugin.py
    ├── services/
    │   ├── __init__.py
    │   ├── cli_runner.py
    │   └── selection_reader.py
    ├── ui/
    │   ├── __init__.py
    │   └── settings_dialog.py
    └── resources/
        └── (icons)
```

### Building a Release

```bash
cd ggu-qgis-tools
zip -r ggu-qgis-plugin.zip ggu-qgis-plugin/
```

## License

MIT License - see [LICENSE](LICENSE)

## Related

- [GGU-CONNECT](https://www.ggu-software.com/ggu-connect) - Geotechnical data management
- [GGU-STRATIG](https://www.ggu-software.com/ggu-stratig) - Borehole visualization
- [DEV-2838](https://ggu-software.atlassian.net/browse/DEV-2838) - Jira ticket for this plugin
