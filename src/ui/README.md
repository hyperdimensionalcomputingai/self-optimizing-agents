# Self-Optimizing Agents UI

This is the React frontend for the Self-Optimizing Agents project, specifically designed for FHIR Graph RAG (Retrieval-Augmented Generation) functionality.

## Features

- Interactive chat interface for querying FHIR data
- Real-time graph visualization
- Debug sidebar for viewing ontology and graph context
- Hybrid RAG pipeline integration (Graph + Vector + FTS)

## Available Scripts

In the project directory, you can run:

### `npm start`

Runs the app in development mode on port 8172.\
Open [http://localhost:8172](http://localhost:8172) to view it in the browser.

The page will reload when you make changes.\
You may also see any lint errors in the console.

### `npm test`

Launches the test runner in the interactive watch mode.

### `npm run build`

Builds the app for production to the `build` folder.\
It correctly bundles React in production mode and optimizes the build for the best performance.

The build is minified and the filenames include the hashes.\
Your app is ready to be deployed!

### `npm run eject`

**Note: this is a one-way operation. Once you `eject`, you can't go back!**

If you aren't satisfied with the build tool and configuration choices, you can `eject` at any time. This command will remove the single-build dependency from your project.

## Backend Integration

This UI connects to a FastAPI backend running on `http://localhost:8001`. The backend provides:

- `/query` - Main endpoint for running the hybrid RAG pipeline
- `/health` - Health check endpoint

## Project Structure

- `src/components/` - React components for the chat interface
- `src/services/` - API service layer
- `src/types/` - TypeScript type definitions
- `public/` - Static assets

## Development

### Using just (Recommended)

The project uses `just` for task management. Install it with `brew install just` if you haven't already.

**Production mode (single command):**
```bash
just start
```
The UI and API will both be available at [http://localhost:8001](http://localhost:8001)

**Development mode (separate terminals):**
```bash
# Terminal 1: Start backend
just api

# Terminal 2: Start frontend
just ui-dev
```

In development mode, the UI will be available at [http://localhost:8172](http://localhost:8172) and the API at [http://localhost:8001](http://localhost:8001).

**Other useful commands:**
- `just install` - Install all dependencies
- `just check` - Check if everything is set up correctly
- `just help` - Show all available commands

### Manual Development

1. Start the backend API server: `uv run src/api_server.py`
2. Start the React development server: `npm start`
3. Open [http://localhost:8172](http://localhost:8172) in your browser (development) or [http://localhost:8001](http://localhost:8001) (production)

## Learn More

- [React documentation](https://reactjs.org/)
- [Create React App documentation](https://facebook.github.io/create-react-app/docs/getting-started)
