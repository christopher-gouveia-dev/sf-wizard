# SF Wizard - Salesforce Utility

A lightweight, modern Salesforce utility tool for generating WHERE IN queries from Excel files and managing Salesforce metadata operations.

## Features

- **WHERE IN Query Generator**: Generate `WHERE IN` queries from Excel columns
- **Workspace Management**: Organize and track multiple Excel projects
- **Version Control**: Automatic versioning of generated files
- **Modern UI**: Vue 3 + Tailwind CSS with CDN (no build step required)
- **Minimal Dependencies**: Uses only stdlib for server (http.server) + openpyxl for Excel

## Requirements

- Python 3.8+
- openpyxl (for Excel handling)
- et-xmlfile (dependency of openpyxl)

## Installation

### Quick Setup

```bash
python install.py
```

This script will:
- Show you the estimated download size for all dependencies
- Ask for confirmation before installing
- Install required packages with pip
- Display installation summary

### Manual Installation

If you prefer manual setup:

```bash
pip install openpyxl et-xmlfile
```

## Usage

### Starting the Server

```bash
python app.py
```

The application will start at `http://localhost:8000`

### Project Structure

```
v2-work/
├── app.py                    # Main server (http.server + routing)
├── workspace_manager.py      # Workspace and Excel management
├── excel_generator.py        # WHERE IN query generation logic
├── install.py               # Dependency installer
├── requirements.txt         # Python dependencies (reference only)
├── README.md               # This file
├── templates/
│   └── index.html          # Vue 3 + Tailwind UI
└── excel-files/            # Workspace data directory (auto-created)
    └── [workspace-name]/
        ├── original/       # Original uploaded file
        ├── current/        # Currently active file
        └── versions/       # Generated versions
```

## Workflow

### 1. Create a Workspace

- Enter a workspace name
- Upload an Excel file (.xlsx or .xls)
- The system creates: `original/`, `current/`, and `versions/` directories

### 2. Generate WHERE IN Query

- Select a source column from your Excel file
- Provide a name for the generator
- Specify the WHERE column name
- Optionally add base SOQL query
- Click "Generate" to create a versioned file

### 3. Version Management

Generated files are automatically versioned:
- Format: `{workspace}_v{N}_{generator_name}.xlsx`
- Each generation creates a new version

## Features Details

### Workspace Management

- **List existing workspaces**: See all previously created projects
- **Create new workspace**: Upload Excel files and organize by project
- **Auto-versioning**: All generated files are automatically versioned

### Column Detection

The system automatically detects:
- **Named tables**: `TableName[ColumnName]`
- **Sheet columns**: `SheetName!A:A`
- Provides autocomplete suggestions when entering source

### Query Generation

Supports multiple source formats:
- Excel tables with structured references
- Regular sheet columns with headers
- Automatic UNIQUE and FILTER formulas

## Architecture

### Backend (Python)

- **http.server**: Standard library HTTP server
- **Custom routing**: Simple, maintainable routing system
- **No external framework**: Minimal dependencies

### Frontend (JavaScript)

- **Vue 3**: Progressive JavaScript framework (CDN)
- **Tailwind CSS**: Utility-first CSS framework (CDN)
- **No build step**: All code runs directly in browser

## API Endpoints

### GET Endpoints

- `GET /api/workspaces` - List all workspaces
- `GET /api/workspace-info?workspace={name}` - Get workspace details
- `GET /api/columns?workspace={name}` - Get available columns from Excel

### POST Endpoints

- `POST /api/upload-excel` - Upload/create new workspace
- `POST /api/generate-where-in` - Generate WHERE IN query

## Future Enhancements

- Bulk API integration for executing queries
- Salesforce metadata deployment with intelligent merging
- Custom labels and translations handling
- Profile and permission set management
- Dry-run execution before actual deployment

## Development Notes

### Adding Dependencies

Edit `install.py` to add new packages:

```python
DEPENDENCIES = {
    "package-name": "version",
}
```

### Configuration

Server host and port can be modified in `app.py`:

```python
run_server(host="0.0.0.0", port=8000)
```

## Troubleshooting

### Port Already in Use

Change the port in `app.py`:

```python
if __name__ == "__main__":
    run_server(port=8001)  # Use different port
```

### Excel File Not Loading

- Ensure file is valid .xlsx format
- Check file is not corrupted
- Try uploading the file again

### Missing Columns

- Verify Excel file has headers
- Check that columns are not in hidden rows
- Reload the workspace

## License

Proprietary - Salesforce Utility

## Support

For issues or feature requests, refer to the project documentation or contact the development team.

Puis ouvrir :
http://localhost:5000

## Ce que fait la V1
- Ajoute 2 feuilles :
  - N - <Nom>
  - N - SOQL <Nom>
- Génère les requêtes WHERE IN par lot
- Compatible Excel Online / Desktop

## Limitations
- Pas de Bulk API
- Pas de Salesforce CLI
- Paramètres fixes (batch=500)